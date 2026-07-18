import AVFoundation
import CoreGraphics
import CoreVideo
import Foundation
import ImageIO

struct Manifest: Decodable {
    let width: Int
    let height: Int
    let scenes: [Scene]
}

struct Scene: Decodable {
    let scene_id: String
    let narration: String
    let frame: String
    let audio: String
}

struct TimelineScene: Encodable {
    let scene_id: String
    let start_seconds: Double
    let end_seconds: Double
    let narration: String
}

enum RenderError: Error {
    case invalidArguments
    case imageLoadFailed(String)
    case pixelBufferFailed
    case writerFailed(String)
    case missingTrack(String)
    case exportFailed(String)
    case durationTooLong(Double)
}

func pixelBuffer(from url: URL, width: Int, height: Int) throws -> CVPixelBuffer {
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil)
    else {
        throw RenderError.imageLoadFailed(url.lastPathComponent)
    }
    var buffer: CVPixelBuffer?
    let attributes: [CFString: Any] = [
        kCVPixelBufferCGImageCompatibilityKey: true,
        kCVPixelBufferCGBitmapContextCompatibilityKey: true,
    ]
    let status = CVPixelBufferCreate(
        kCFAllocatorDefault,
        width,
        height,
        kCVPixelFormatType_32BGRA,
        attributes as CFDictionary,
        &buffer
    )
    guard status == kCVReturnSuccess, let buffer else {
        throw RenderError.pixelBufferFailed
    }
    CVPixelBufferLockBaseAddress(buffer, [])
    defer { CVPixelBufferUnlockBaseAddress(buffer, []) }
    guard let context = CGContext(
        data: CVPixelBufferGetBaseAddress(buffer),
        width: width,
        height: height,
        bitsPerComponent: 8,
        bytesPerRow: CVPixelBufferGetBytesPerRow(buffer),
        space: CGColorSpaceCreateDeviceRGB(),
        bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue
            | CGBitmapInfo.byteOrder32Little.rawValue
    ) else {
        throw RenderError.pixelBufferFailed
    }
    context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
    return buffer
}

func waitUntilReady(_ input: AVAssetWriterInput) {
    while !input.isReadyForMoreMediaData {
        Thread.sleep(forTimeInterval: 0.005)
    }
}

func finish(_ writer: AVAssetWriter) async {
    await withCheckedContinuation { continuation in
        writer.finishWriting {
            continuation.resume()
        }
    }
}

func secondsToSRT(_ value: Double) -> String {
    let milliseconds = Int((value * 1000.0).rounded())
    let hours = milliseconds / 3_600_000
    let minutes = (milliseconds % 3_600_000) / 60_000
    let seconds = (milliseconds % 60_000) / 1000
    let remainder = milliseconds % 1000
    return String(format: "%02d:%02d:%02d,%03d", hours, minutes, seconds, remainder)
}

func subtitleSentences(_ narration: String) -> [String] {
    var sentences: [String] = []
    narration.enumerateSubstrings(
        in: narration.startIndex ..< narration.endIndex,
        options: [.bySentences, .substringNotRequired]
    ) { _, range, _, _ in
        let sentence = narration[range].trimmingCharacters(in: .whitespacesAndNewlines)
        if !sentence.isEmpty {
            sentences.append(sentence)
        }
    }
    return sentences.isEmpty ? [narration] : sentences
}

func wrapSubtitle(_ text: String, width: Int = 54) -> String {
    var lines: [String] = []
    var line = ""
    for word in text.split(separator: " ").map(String.init) {
        let candidate = line.isEmpty ? word : "\(line) \(word)"
        if candidate.count <= width {
            line = candidate
        } else {
            if !line.isEmpty {
                lines.append(line)
            }
            line = word
        }
    }
    if !line.isEmpty {
        lines.append(line)
    }
    return lines.joined(separator: "\n")
}

@main
struct DemoRenderer {
    static func main() async throws {
        guard CommandLine.arguments.count == 6 else {
            throw RenderError.invalidArguments
        }
        let manifestURL = URL(fileURLWithPath: CommandLine.arguments[1])
        let framesURL = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
        let audioURL = URL(fileURLWithPath: CommandLine.arguments[3], isDirectory: true)
        let outputURL = URL(fileURLWithPath: CommandLine.arguments[4])
        let timelineURL = URL(fileURLWithPath: CommandLine.arguments[5])
        let outputDirectory = outputURL.deletingLastPathComponent()
        let silentURL = outputDirectory.appendingPathComponent("lineageproof-demo-silent.mp4")
        let srtURL = outputDirectory.appendingPathComponent("LineageProof_Demo_en.srt")
        try FileManager.default.createDirectory(
            at: outputDirectory,
            withIntermediateDirectories: true
        )
        for url in [silentURL, outputURL, timelineURL, srtURL] where FileManager.default.fileExists(atPath: url.path) {
            try FileManager.default.removeItem(at: url)
        }

        let manifest = try JSONDecoder().decode(
            Manifest.self,
            from: Data(contentsOf: manifestURL)
        )
        let gapSeconds = 0.65
        var durations: [CMTime] = []
        for scene in manifest.scenes {
            let asset = AVURLAsset(url: audioURL.appendingPathComponent(scene.audio))
            durations.append(try await asset.load(.duration))
        }
        let narrationDuration = durations.reduce(CMTime.zero, +)
        let expectedDuration = narrationDuration + CMTime(
            seconds: gapSeconds * Double(manifest.scenes.count),
            preferredTimescale: 600
        )
        let expectedSeconds = CMTimeGetSeconds(expectedDuration)
        guard expectedSeconds < 180.0 else {
            throw RenderError.durationTooLong(expectedSeconds)
        }

        let writer = try AVAssetWriter(outputURL: silentURL, fileType: .mp4)
        let videoSettings: [String: Any] = [
            AVVideoCodecKey: AVVideoCodecType.h264,
            AVVideoWidthKey: manifest.width,
            AVVideoHeightKey: manifest.height,
            AVVideoCompressionPropertiesKey: [
                AVVideoAverageBitRateKey: 7_000_000,
                AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
            ],
        ]
        let videoInput = AVAssetWriterInput(mediaType: .video, outputSettings: videoSettings)
        videoInput.expectsMediaDataInRealTime = false
        let adaptor = AVAssetWriterInputPixelBufferAdaptor(
            assetWriterInput: videoInput,
            sourcePixelBufferAttributes: [
                kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
                kCVPixelBufferWidthKey as String: manifest.width,
                kCVPixelBufferHeightKey as String: manifest.height,
            ]
        )
        guard writer.canAdd(videoInput) else {
            throw RenderError.writerFailed("cannot add video input")
        }
        writer.add(videoInput)
        guard writer.startWriting() else {
            throw RenderError.writerFailed(writer.error?.localizedDescription ?? "start failed")
        }
        writer.startSession(atSourceTime: .zero)

        var timeline: [TimelineScene] = []
        var cursor = CMTime.zero
        let minimumFrame = CMTime(value: 1, timescale: 30)
        for (index, scene) in manifest.scenes.enumerated() {
            let frame = try pixelBuffer(
                from: framesURL.appendingPathComponent(scene.frame),
                width: manifest.width,
                height: manifest.height
            )
            waitUntilReady(videoInput)
            guard adaptor.append(frame, withPresentationTime: cursor) else {
                throw RenderError.writerFailed(writer.error?.localizedDescription ?? "append failed")
            }
            let sceneDuration = durations[index] + CMTime(seconds: gapSeconds, preferredTimescale: 600)
            let end = cursor + sceneDuration
            waitUntilReady(videoInput)
            guard adaptor.append(frame, withPresentationTime: end - minimumFrame) else {
                throw RenderError.writerFailed(writer.error?.localizedDescription ?? "append failed")
            }
            timeline.append(
                TimelineScene(
                    scene_id: scene.scene_id,
                    start_seconds: CMTimeGetSeconds(cursor),
                    end_seconds: CMTimeGetSeconds(cursor + durations[index]),
                    narration: scene.narration
                )
            )
            cursor = end
        }
        writer.endSession(atSourceTime: cursor)
        videoInput.markAsFinished()
        await finish(writer)
        guard writer.status == .completed else {
            throw RenderError.writerFailed(writer.error?.localizedDescription ?? "finish failed")
        }

        let composition = AVMutableComposition()
        guard let compositionVideo = composition.addMutableTrack(
            withMediaType: .video,
            preferredTrackID: kCMPersistentTrackID_Invalid
        ), let compositionAudio = composition.addMutableTrack(
            withMediaType: .audio,
            preferredTrackID: kCMPersistentTrackID_Invalid
        ) else {
            throw RenderError.missingTrack("composition tracks")
        }
        let silentAsset = AVURLAsset(url: silentURL)
        guard let silentTrack = try await silentAsset.loadTracks(withMediaType: .video).first else {
            throw RenderError.missingTrack("silent video")
        }
        let silentDuration = try await silentAsset.load(.duration)
        try compositionVideo.insertTimeRange(
            CMTimeRange(start: .zero, duration: silentDuration),
            of: silentTrack,
            at: .zero
        )

        cursor = .zero
        for (index, scene) in manifest.scenes.enumerated() {
            let asset = AVURLAsset(url: audioURL.appendingPathComponent(scene.audio))
            guard let track = try await asset.loadTracks(withMediaType: .audio).first else {
                throw RenderError.missingTrack(scene.audio)
            }
            try compositionAudio.insertTimeRange(
                CMTimeRange(start: .zero, duration: durations[index]),
                of: track,
                at: cursor
            )
            cursor = cursor + durations[index] + CMTime(seconds: gapSeconds, preferredTimescale: 600)
        }

        guard let exporter = AVAssetExportSession(
            asset: composition,
            presetName: AVAssetExportPresetHighestQuality
        ) else {
            throw RenderError.exportFailed("cannot create exporter")
        }
        try await exporter.export(to: outputURL, as: .mp4)

        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(timeline).write(to: timelineURL)
        var srt = ""
        var cue = 1
        for item in timeline {
            let sentences = subtitleSentences(item.narration)
            let totalWeight = sentences.reduce(0) { $0 + max($1.count, 1) }
            var cueStart = item.start_seconds
            for (index, sentence) in sentences.enumerated() {
                let isLast = index == sentences.count - 1
                let share = Double(max(sentence.count, 1)) / Double(totalWeight)
                let proportionalEnd = cueStart + (item.end_seconds - item.start_seconds) * share
                let cueEnd = isLast ? item.end_seconds : min(proportionalEnd, item.end_seconds)
                srt += "\(cue)\n"
                srt += "\(secondsToSRT(cueStart)) --> \(secondsToSRT(cueEnd))\n"
                srt += "\(wrapSubtitle(sentence))\n\n"
                cue += 1
                cueStart = cueEnd
            }
        }
        try srt.write(to: srtURL, atomically: true, encoding: .utf8)

        let finalAsset = AVURLAsset(url: outputURL)
        let finalDuration = try await finalAsset.load(.duration)
        let videoTracks = try await finalAsset.loadTracks(withMediaType: .video)
        let audioTracks = try await finalAsset.loadTracks(withMediaType: .audio)
        let result: [String: Any] = [
            "audio_tracks": audioTracks.count,
            "duration_seconds": CMTimeGetSeconds(finalDuration),
            "height": manifest.height,
            "output": outputURL.lastPathComponent,
            "scenes": manifest.scenes.count,
            "status": "pass",
            "video_tracks": videoTracks.count,
            "width": manifest.width,
        ]
        let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
        print(String(decoding: data, as: UTF8.self))
    }
}
