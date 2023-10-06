# qrcode-file-tx
Transferring Files via QRCode &amp; Camera(Video File)

# Needed python packages
```
pip3 install pillow pyqt5 opencv-python qrcode numpy pyzbar
```
If you are on macOS, maybe you have to install the `zbar` library by homebrew (It is needed by `pyzbar`)
```
brew install zbar
```

# How to use
1. Edit `qrcode_play.py`, change `FILE_NAME` to your file.

2. The parameter (E.g. `QRCODE_SIZE`, `QRCODE_NUMBER`, `FRAME_RATE`, etc.) is works well on my computer (1080p 23inch screen) and my phone(60FPS 1080p video recording). You can adjust these parameters as you need. For example, if you only can record 30FPS video, you can try to reduce the framerate. 

3. Chunk size must be the power of 2.

4. If you found the QR Code can not display correctly, try to adjust the QRCode size, QR Code number per row, chunk size (smaller chunk size can make the QR Code smaller, even with the same QRCode size), number of QR Code, etc.

5. Run `qrcode_play.py`. Notice: it will save the QR Code cache to `qr_cache.pickle`. Next time it will load QR code from this file to save time, if the parameters has not been changed. If you want to re-generate QR code, please delete `qr_cache.pickle`.

6. Record a video of the QR code. Try to use higher video bitrate as much as possible.

7. Edit `decode_video.py`, change `VIDEO_FILE` to your video file name. If you changed `QRCODE_NUMBER` in `qrcode_play.py`, you also have to change here.

8. If the video can be decoded successfully, a `output.bin` will be generated. This should be as same as your input file. 