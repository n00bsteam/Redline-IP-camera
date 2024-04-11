# Redline-IP-camera
Redline IP camera video downloader

## Quick start:
- Clone this repo & Change variables
```
cd /opt/
git clone https://github.com/n00bsteam/Redline-IP-camera.git
nano Redline-IP-camera/main.py
```
- Add to crontab task
```
*/5 * * * * python3 /opt/Redline-IP-camera/main.py >> /opt/redline.log
``` 