import requests
import os
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
from datetime import datetime

# 配置信息
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
MY_ACCOUNTS = ["MeowCracker", "GamerNoTitle"]  # 需要监控的账户

def is_my_repo(repo_name):
    """判断是否属于我的仓库"""
    return any(repo_name.startswith(f"{user}/") for user in MY_ACCOUNTS)

def parse_event(event):
    """解析并过滤事件"""
    event_type = event['type']
    actor = event['actor']['login']
    repo_name = event['repo']['name']
    payload = event['payload']

    # 排除自己账户触发的事件
    if actor in MY_ACCOUNTS:
        return None

    # 仅处理我的仓库相关事件
    if not is_my_repo(repo_name):
        return None

    # 精确事件过滤
    event_data = {
        'id': event['id'],
        'created_at': datetime.strptime(event['created_at'], "%Y-%m-%dT%H:%M:%SZ"),
        'repo': repo_name
    }

    if event_type == "WatchEvent" and payload.get("action") == "started":
        event_data.update({
            'type': 'star',
            'desc': f"{actor} star了仓库 {repo_name}",
            'link': f"https://github.com/{repo_name}/stargazers"
        })
    
    elif event_type == "ForkEvent":
        event_data.update({
            'type': 'fork',
            'desc': f"{actor} fork了仓库 {repo_name}",
            'link': payload['forkee']['html_url']
        })
    
    elif event_type == "IssuesEvent" and payload.get('action') == 'opened':
        event_data.update({
            'type': 'issue',
            'desc': f"{actor} 创建了Issue: {payload['issue']['title']}",
            'link': payload['issue']['html_url'],
            'details': payload['issue']['body']
        })
    
    elif event_type == "IssueCommentEvent" and payload.get('action') == 'created':
        if payload['issue']['user']['login'] in MY_ACCOUNTS:
            event_data.update({
                'type': 'issue_reply',
                'desc': f"{actor} 回复了你的Issue: {payload['issue']['title']}",
                'link': payload['comment']['html_url'],
                'details': payload['comment']['body']
            })
    
    elif event_type == "PullRequestEvent" and payload.get('action') == 'opened':
        event_data.update({
            'type': 'pr',
            'desc': f"{actor} 提交了PR: {payload['pull_request']['title']}",
            'link': payload['pull_request']['html_url'],
            'details': payload['pull_request']['body']
        })
    
    elif event_type == "PullRequestReviewCommentEvent":
        if payload['pull_request']['user']['login'] in MY_ACCOUNTS:
            event_data.update({
                'type': 'pr_review',
                'desc': f"{actor} 评审了你的PR: {payload['pull_request']['title']}",
                'link': payload['comment']['html_url'],
                'details': payload['comment']['body']
            })
    
    else:
        return None

    return event_data

def generate_rss(events):
    """生成RSS"""
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    
    ET.SubElement(channel, "title").text = "我的GitHub动态追踪"
    ET.SubElement(channel, "link").text = "https://github.com"
    ET.SubElement(channel, "description").text = "精选仓库活动监控"

    for event in sorted(events, key=lambda x: x['created_at'], reverse=True):
        item = ET.Element("item")
        ET.SubElement(item, "title").text = event['desc']
        ET.SubElement(item, "link").text = event['link']
        ET.SubElement(item, "guid").text = event['id']
        ET.SubElement(item, "pubDate").text = event['created_at'].strftime("%a, %d %b %Y %H:%M:%S +0000")
        
        if 'details' in event:
            desc = ET.SubElement(item, "description")
            desc.text = escape(f"内容：{event['details'][:200]}...") if event['details'] else "无附加内容"
        
        channel.append(item)

    return rss

def main():
    all_events = []
    
    for user in MY_ACCOUNTS:
        url = f"https://api.github.com/users/{user}/received_events/public"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            for event in response.json():
                if parsed := parse_event(event):
                    all_events.append(parsed)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching events for {user}: {e}")

    rss = generate_rss(all_events)
    
    # 保存文件
    tree = ET.ElementTree(rss)
    ET.indent(tree, '  ')
    xml_str = ET.tostring(rss, encoding='utf-8', method='xml').decode()
    
    with open("activity.xml", "w", encoding='utf-8') as f:
        f.write(f'<?xml version="1.0" encoding="utf-8"?>\n{xml_str}')

if __name__ == "__main__":
    main()
