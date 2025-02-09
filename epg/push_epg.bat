@echo off
cd C:\Users\James\Documents\M3U-Playlist\epg

:: Stage the changes for commit
git add ../epg/guide.xml
git add ../epg/run_epg.bat

:: Commit the changes
git commit -m "Auto-updated guide.xml"

:: Push to GitHub
git push origin main

echo Pushed at %DATE% %TIME% >> epg_push_log.txt
