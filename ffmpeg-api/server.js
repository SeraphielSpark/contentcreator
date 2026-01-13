const express = require("express");
const multer = require("multer");
const { exec } = require("child_process");
const path = require("path");
const fs = require("fs");
const cors = require("cors");

const app = express();
app.use(cors());

const upload = multer({ dest: "uploads/" });

app.post("/convert", upload.single("audio"), (req, res) => {
  if (!req.file) {
    return res.status(400).send("No audio file");
  }

  const inputPath = req.file.path;
  const outputPath = `${inputPath}.ogg`;

  const cmd = `
    ffmpeg -y -i ${inputPath} \
    -c:a libopus -b:a 32k -ar 48000 -ac 1 \
    ${outputPath}
  `;

  exec(cmd, (error) => {
    if (error) {
      console.error(error);
      return res.status(500).send("Conversion failed");
    }

    res.setHeader("Content-Type", "audio/ogg");
    res.setHeader("Content-Disposition", "attachment; filename=voice.ogg");

    fs.createReadStream(outputPath).pipe(res);

    // cleanup
    setTimeout(() => {
      fs.unlinkSync(inputPath);
      fs.unlinkSync(outputPath);
    }, 5000);
  });
});

app.listen(3000, () => {
  console.log("FFmpeg API running on port 3000");
});
