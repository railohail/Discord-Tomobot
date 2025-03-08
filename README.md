# Setup
## first you have to already have a bot
## make your own .env file 
windows
```
copy envexample.txt .env 
```
the inside should look like this 
```
# Discord settings
DISCORD_BOT_TOKEN=
DISCORD_GUILD=

# Lavalink settings
LAVALINK_HOST=lavalink
LAVALINK_PORT=2333
LAVALINK_PASSWORD=youshallnotpass

# YouTube settings (generate these using youtube-trusted-session-generator)
YOUTUBE_PO_TOKEN=
YOUTUBE_VISITOR_DATA=
YOUTUBE_PLUGIN_VER=dev.lavalink.youtube:youtube-plugin:1.11.5
```
## fill the DISCORD_BOT_TOKEN and DISCORD_GUILD with discord developer portal and discord developer mode in your discord
## fill the YOUTUBE_PO_TOKEN YOUTUBE_VISITOR_DATA
1. clone the youtube-trusted-session-generator repo
```
git clone https://github.com/iv-org/youtube-trusted-session-generator.git
```
2. Run the script: `docker run quay.io/invidious/youtube-trusted-session-generator`
3. Copy paste the values of these the two parameters (po_token and visitor_data) 
   ```
   po_token: XXX
   visitor_data: XXX
   ```
## make sure your YOUTUBE_PLUGIN_VER is the newest 
https://github.com/lavalink-devs/youtube-source/releases
# Deploy via Docker Compose
```
docker-compose up -d
```
