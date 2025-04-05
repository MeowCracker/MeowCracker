import requests
import os
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
from datetime import datetime

# 配置信息
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
USERNAME = "MeowCracker"
API_URL = f"https://api.github.com/users/{USERNAME}/received_events/public"

def parse_event(event):
    """将GitHub事件转换为RSS条目"""
    event_type = event['type']
    actor_login = event['actor']['display_login']
    repo_name = event['repo']['name']
    created_at = datetime.strptime(event['created_at'], "%Y-%m-%dT%H:%M:%SZ")
    
    # 构建基础元素
    item = ET.Element("item")
    ET.SubElement(item, "title").text = f"{actor_login} 在 {repo_name} 的 {event_type}"
    ET.SubElement(item, "link").text = f"https://github.com/{repo_name}"
    ET.SubElement(item, "guid").text = event['id']
    ET.SubElement(item, "pubDate").text = created_at.strftime("%a, %d %b %Y %H:%M:%S +0000")
    
    # 根据事件类型生成描述
    description = ET.SubElement(item, "description")
    payload = event['payload']
    
    if event_type == "PushEvent":
        commits = [f"{c['message']} (commit: {c['sha'][:7]})" for c in payload['commits']]
        desc_text = f"{actor_login} 提交了 {len(commits)} 个变更：\n" + "\n".join(commits)
    elif event_type == "WatchEvent":
        desc_text = f"{actor_login} 关注了仓库 {repo_name}"
    elif event_type == "CreateEvent":
        ref_type = payload['ref_type']
        desc_text = f"新建 {ref_type}：{payload.get('ref', '')} @ {repo_name}"
    else:
        desc_text = f"{event_type} 事件发生于 {repo_name}"
    
    description.text = escape(desc_text)
    return item

# 获取GitHub事件数据
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28"
}

response = requests.get(API_URL, headers=headers)
events = response.json()

# 构建RSS结构
rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")

ET.SubElement(channel, "title").text = f"{USERNAME} 的GitHub动态"
ET.SubElement(channel, "link").text = f"https://github.com/{USERNAME}"
ET.SubElement(channel, "description").text = "GitHub事件订阅"

# 添加事件条目
for event in events:
    channel.append(parse_event(event))

# 生成XML字符串
tree = ET.ElementTree(rss)
ET.indent(tree, '  ')
xml_str = ET.tostring(rss, encoding='utf-8', method='xml').decode()

with open("activity.xml", "wt") as f:
  f.write(f'<?xml version="1.0" encoding="utf-8"?>\n{xml_str}')
