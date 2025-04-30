import os
from datetime import datetime
from xml.sax.saxutils import escape

def generate_rss(posts, site_url, output_path):
    rss_items = []
    for post in posts[:20]:  # Limit to latest 20 posts
        item = f"""
    <item>
      <title>{escape(post['title'])}</title>
      <link>{site_url}/{post['slug']}.html</link>
      <guid>{site_url}/{post['slug']}.html</guid>
      <pubDate>{post['date_obj'].strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
      <description><![CDATA[{post.get('summary','')[:300]}]]></description>
    </item>"""
        rss_items.append(item)
    rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Your Dropshipping Store Blog</title>
  <link>{site_url}/blog.html</link>
  <description>Latest dropshipping tips, trends, and product news.</description>
  <language>en-us</language>
  <lastBuildDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
  {''.join(rss_items)}
</channel>
</rss>'''
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rss)

# To use in generate_blog.py:
# from generate_rss import generate_rss
# generate_rss(posts, 'https://yourdomain.com', os.path.join(OUTPUT_DIR, 'rss.xml'))
