# ✅ Deployment Checklist

## Pre-Deployment (On Your Local Machine)

- [ ] Verify project works locally
  ```bash
  python run_backend.py
  ```
- [ ] Test with sample PDF upload
- [ ] Check all assets are present:
  - [ ] `assets/fonts/Book Antiqua.ttf`
  - [ ] `assets/backgrounds/*.jpg` (3 background images)
- [ ] Get API keys ready:
  - [ ] OpenAI API Key (REQUIRED)
  - [ ] Cartesia API Key (optional)

## Server Setup

- [ ] Server has Python 3.10+ installed
  ```bash
  python3 --version
  ```
- [ ] FFmpeg installed
  ```bash
  ffmpeg -version
  ```
- [ ] Sufficient disk space (20GB+ recommended)
  ```bash
  df -h
  ```
- [ ] Sufficient RAM (4GB+ recommended)
  ```bash
  free -h
  ```

## File Transfer

- [ ] Upload entire `Pdf_Video_Generation/` directory to server
- [ ] Verify directory structure on server:
  ```
  Pdf_Video_Generation/
  ├── app/              ✓
  ├── assets/           ✓
  ├── requirements.txt  ✓
  ├── run_backend.py    ✓
  └── .env              ✗ (will create)
  ```

## Environment Setup

- [ ] Create virtual environment
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- [ ] Install dependencies
  ```bash
  pip install -r requirements.txt
  ```
- [ ] Create `.env` file with API keys
  ```bash
  nano .env
  ```
  ```env
  OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
  VIDEO_FPS=30
  VIDEO_WIDTH=1920
  VIDEO_HEIGHT=1080
  ```
- [ ] Set `.env` permissions
  ```bash
  chmod 600 .env
  ```

## Testing

- [ ] Test run backend
  ```bash
  python run_backend.py
  ```
- [ ] Test health endpoint
  ```bash
  curl http://localhost:8000/health
  ```
- [ ] Upload test PDF (in another terminal)
  ```bash
  curl -X POST "http://localhost:8000/api/upload" \
    -F "file=@test.pdf" \
    -F "start_page=1" \
    -F "end_page=1"
  ```
- [ ] Check job status
  ```bash
  curl http://localhost:8000/api/jobs/{job_id}
  ```

## Production Setup (Choose One)

### Option A: Systemd Service (Recommended)
- [ ] Create service file
  ```bash
  sudo nano /etc/systemd/system/pdf-video-api.service
  ```
- [ ] Start service
  ```bash
  sudo systemctl start pdf-video-api
  sudo systemctl enable pdf-video-api
  ```
- [ ] Check service status
  ```bash
  sudo systemctl status pdf-video-api
  ```

### Option B: Screen/Tmux (Quick & Dirty)
- [ ] Install screen
  ```bash
  sudo apt install screen -y
  ```
- [ ] Run in screen
  ```bash
  screen -S pdf-video-api
  python run_backend.py
  # Press Ctrl+A, then D to detach
  ```
- [ ] Reattach later
  ```bash
  screen -r pdf-video-api
  ```

## Nginx Reverse Proxy (Optional)

- [ ] Install Nginx
  ```bash
  sudo apt install nginx -y
  ```
- [ ] Create config file
  ```bash
  sudo nano /etc/nginx/sites-available/pdf-video-api
  ```
- [ ] Enable site
  ```bash
  sudo ln -s /etc/nginx/sites-available/pdf-video-api /etc/nginx/sites-enabled/
  sudo nginx -t
  sudo systemctl restart nginx
  ```

## SSL Certificate (Optional)

- [ ] Install Certbot
  ```bash
  sudo apt install certbot python3-certbot-nginx -y
  ```
- [ ] Get certificate
  ```bash
  sudo certbot --nginx -d your-domain.com
  ```

## Security

- [ ] Firewall rules configured
  ```bash
  sudo ufw allow 22/tcp   # SSH
  sudo ufw allow 80/tcp   # HTTP
  sudo ufw allow 443/tcp  # HTTPS
  sudo ufw enable
  ```
- [ ] `.env` file NOT committed to git
  ```bash
  git status  # Should NOT show .env
  ```
- [ ] API key has sufficient credits
  - Check: https://platform.openai.com/usage

## Final Verification

- [ ] Backend accessible from external IP
  ```bash
  curl http://your-server-ip:8000/health
  ```
- [ ] Upload and process a real PDF
- [ ] Download generated video successfully
- [ ] Check logs for errors
  ```bash
  tail -f logs/*.log
  ```
- [ ] Monitor disk space usage
  ```bash
  du -sh jobs/
  ```

## Post-Deployment Monitoring

- [ ] Set up log rotation
  ```bash
  sudo nano /etc/logrotate.d/pdf-video-api
  ```
- [ ] Monitor API usage (OpenAI dashboard)
- [ ] Check disk space regularly
  ```bash
  df -h
  ```
- [ ] Backup jobs directory if needed
  ```bash
  rsync -av jobs/ /backup/location/
  ```

## Documentation

- [ ] Note your server IP/domain: `________________`
- [ ] Note API endpoint: `http://________________:8000`
- [ ] Save OpenAI API key securely: `________________`
- [ ] Document any custom configurations

---

## Quick Commands Reference

```bash
# Start backend (development)
python run_backend.py

# Start backend (production with Gunicorn)
gunicorn app.api.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Check service status
sudo systemctl status pdf-video-api

# View logs
tail -f logs/*.log
sudo journalctl -u pdf-video-api -f

# Check running processes
ps aux | grep uvicorn

# Kill process if needed
pkill -f uvicorn

# Check disk space
df -h
du -sh jobs/

# Clean old jobs (if needed)
find jobs/ -type d -mtime +7 -exec rm -rf {} +
```

---

## Troubleshooting Quick Fixes

**Backend won't start:**
```bash
# Check Python version
python3 --version

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Check .env file
cat .env | grep OPENAI_API_KEY
```

**API key errors:**
```bash
# Verify .env file exists
ls -la .env

# Check if key is loaded
python3 -c "from app.config import settings; print(len(settings.OPENAI_API_KEY))"
```

**FFmpeg errors:**
```bash
# Install FFmpeg
sudo apt install ffmpeg -y

# Verify installation
ffmpeg -version
```

**Out of disk space:**
```bash
# Check usage
df -h

# Clean old jobs
rm -rf jobs/old_job_id_*/

# Clear pip cache
pip cache purge
```

---

**Need help?** Refer to `HOSTING_GUIDE.md` for detailed explanations!
