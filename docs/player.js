const video = document.querySelector("video[data-captions]");

if (video) {
  fetch(video.dataset.captions)
    .then((response) => {
      if (!response.ok) throw new Error(`Caption request failed: ${response.status}`);
      return response.text();
    })
    .then((srt) => {
      const vtt = `WEBVTT\n\n${srt
        .replace(/\r/g, "")
        .replace(/(\d{2}:\d{2}:\d{2}),(\d{3})/g, "$1.$2")}`;
      const track = document.createElement("track");
      track.kind = "captions";
      track.label = "English";
      track.srclang = "en";
      track.default = true;
      track.src = URL.createObjectURL(new Blob([vtt], { type: "text/vtt" }));
      track.addEventListener("load", () => {
        track.track.mode = "showing";
      });
      video.append(track);
    })
    .catch(() => {
      // The downloadable SRT remains available if a browser blocks dynamic tracks.
    });
}
