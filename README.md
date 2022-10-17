# Mastodon Postbot
This is currently a WIP hacky script for posting to Mastodon, based off of [Tootbot](https://github.com/cquest/tootbot)

## Source
https://github.com/BonzTM/mastodon-postbot

## Features
Will take a Twitter User or Twitter Search and post them natively on Mastodon.
- Includes grabbing and posting embedded photos, multiple embedded photos, or embedded videos directly into the post.

## Example Posts
- [CleGuardians on Mastodon.land](https://mastodon.land/@cleguardians)
- [PlayNewWorld on botsin.space](https://botsin.space/@playnewworld)

## Docker Image
https://hub.docker.com/r/bonztm/mastodon-postbot

## Pre-requisites

- RSS Bridge - This bot only works with RSS Bridge and has no plans to use any other RSS feed building applications at this time.
- Twitter - This bot currently only works with Twitter Users and Twitter Searches/Hashtags

#### Option 1:
- A place to run the script
- Python3
- Local storage for SQLite DB

#### Option 2:
- Docker/Kubernetes - An simple image is built at [DockerHub](https://hub.docker.com/r/bonztm/mastodon-postbot).
- PVC/PV for SQLite storage

## Configuration

The bot works entirely off of ENV Variables.  The following variables MUST be set:
### Required Variables

#### Main Variables
- MASTODON_INSTANCE: The name/url of your mastodon instance, WITHOUT http/https.  Example: mastodon.land
- MASTODON_TOKEN:  A token that you will use to post.
  - (Note:  Please create a bot account, label it such, and create a new token)

#### Additional Variables, Option 1
*Use either option 1, or option 2.  Do not use both*
- RSS_BRIDGE_URL: Full URL to the RSSBridge RSS feed URL.  Will only parse twitter user or twitter search configured URLs.
  - (Note: Useful if you want to customize the URL from RSS Bridge interface)

#### Additional Variables, Option 2
*Use either option 1, or option 2.  Do not use both*
- RSS_BRIDGE_BASE_URL: The BASE url to your rss bridge instance, including http/https prefix and excluding any trailing slashes.  Example: http://rssbridge.cluster.svc.local
  - (Note: Default will retweet, but will not take replies or pinned tweets.  If you want to change this, generate the RSS_BRIDGE_URL yourself)
- TWITTER_USER (optional): in all lowercase, the name of the twitter user you are trying to get an RSS feed for. 
  - (Note1: Do not re-post Twitter user's tweets as yourself on Mastodon) 
  - (Note2: The URL is built as follows: `os.environ.get("RSS_BRIDGE_URL")}/?action=display&bridge=TwitterBridge&context=By+username&u={twitter}&norep=on&nopinned=on&format=Json`, so it requires RSS Bridge to be running)
- TWITTER_SEARCH (optional): in all lowercase, the search or hashtag you wish to post to Mastodon.

## Usage

### Script/Host mode
1. Set all ENV Vars appropriately
2. Download the python script, and 
3. Execute: `python mastodon_postbot.py`

### Docker
```sh example1
docker run -d \
        -e RSS_BRIDGE_BASE_URL='http://rssbridge.cluster.svc.local' \
        -e TWITTER_USER=browns \
        -e MASTODON_INSTANCE=mastodon.land \
        -e MASTODON_TOKEN=<super_secret_token> \
        bonztm/mastodon-postbot:latest
```

```sh example2
docker run -d \
        -e RSS_BRIDGE_URL='http://rssbridge.apps.cluster.home.lan/?action=display&bridge=TwitterBridge&context=By+username&u=browns&norep=on&nopinned=on&format=Html' \
        -e MASTODON_INSTANCE=mastodon.land \
        -e MASTODON_TOKEN=<super_secret_token> \
        bonztm/mastodon-postbot:latest
```
### Kubernetes

Example Statefulset:
```yaml
---
kind: StatefulSet
apiVersion: apps/v1
metadata:
  name: mastodon-postbot-browns
  namespace: mastodon-postbot
  labels:
    app: mastodon-postbot-browns
spec:
  serviceName: mastodon-postbot-browns
  replicas: 1
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: mastodon-postbot-browns
  template:
    metadata:
      labels:
        app: mastodon-postbot-browns
    spec:
      containers:
        - name: mastodon-postbot-browns 
          image: bonztm/mastodon-postbot:latest
          imagePullPolicy: Always
          env:
            - name: RSS_BRIDGE_BASE_URL
              value: http://rssbridge.namespace.svc.cluster.local
            - name: TWITTER_USER
              value: browns
            - name: MASTODON_INSTANCE
              value: mastodon.land
            - name: MASTODON_TOKEN
              valueFrom:
                secretKeyRef:
                  name: mastodon-postbot-secrets
                  key: browns
          securityContext:
            privileged: true
          volumeMounts:
            - name: config
              mountPath: "/config"
      volumes:
        - name: config
          persistentVolumeClaim:
            claimName: mastodon-postbot-browns-persistent-config-storage
  updateStrategy:
    type: RollingUpdate
```

Example PVC:
```yaml
---
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: mastodon-postbot-browns-persistent-config-storage
  namespace: mastodon-postbot
  labels:
    app: mastodon-postbot-browns
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```