import os
import glob
import markdown
import yaml
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# --- CONFIG ---
BLOG_DIR = 'blog'
AUTHOR_DIR = os.path.join(BLOG_DIR, 'authors')
OUTPUT_DIR = 'site'
TEMPLATE_DIR = 'templates'

# --- HELPERS ---
def parse_markdown_with_frontmatter(path):
    with open(path, encoding='utf-8') as f:
        content = f.read()
    if content.startswith('---'):
        _, fm, md = content.split('---', 2)
        frontmatter = yaml.safe_load(fm)
        return frontmatter, md.strip()
    return {}, content

def load_authors():
    authors = {}
    for f in glob.glob(os.path.join(AUTHOR_DIR, '*.md')):
        fm, _ = parse_markdown_with_frontmatter(f)
        authors[fm['id']] = fm
    return authors

def load_posts():
    posts = []
    for f in glob.glob(os.path.join(BLOG_DIR, '*.md')):
        fm, md = parse_markdown_with_frontmatter(f)
        fm['content'] = markdown.markdown(md)
        fm['slug'] = os.path.splitext(os.path.basename(f))[0]
        fm['date_obj'] = datetime.strptime(str(fm['date']), '%Y-%m-%d')
        posts.append(fm)
    return posts

def filter_posts(posts, tag=None, featured=None, before=None):
    result = posts
    if tag:
        result = [p for p in result if tag in p.get('tags', [])]
    if featured is not None:
        result = [p for p in result if p.get('featured', False) == featured]
    if before:
        result = [p for p in result if p['date_obj'] <= before]
    return sorted(result, key=lambda p: p['date_obj'], reverse=True)

def render_site():
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    authors = load_authors()
    posts = load_posts()
    now = datetime.now()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Blog index
    index_tmpl = env.get_template('blog_index.html')
    index_html = index_tmpl.render(posts=filter_posts(posts, before=now), authors=authors)
    with open(os.path.join(OUTPUT_DIR, 'blog.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)

    # Tag pages
    tags = set(t for p in posts for t in p.get('tags', []))
    tag_tmpl = env.get_template('tag.html')
    for tag in tags:
        tag_html = tag_tmpl.render(tag=tag, posts=filter_posts(posts, tag=tag, before=now), authors=authors)
        with open(os.path.join(OUTPUT_DIR, f'tag-{tag}.html'), 'w', encoding='utf-8') as f:
            f.write(tag_html)

    # Author pages
    author_tmpl = env.get_template('author.html')
    for author_id, author_data_from_load in authors.items():
        # Create a mutable copy to work with, to avoid modifying the original loaded authors dict
        author = author_data_from_load.copy()

        # Ensure the 'social' key exists in the author dictionary.
        # If it's not present in the author's MD frontmatter, default it to an empty dictionary.
        # This makes template access like `author.social.twitter` safer,
        # as `author.social` will always exist (though it might be empty).
        author.setdefault('social', {})

        author_posts = [p for p in posts if p.get('author') == author_id and p['date_obj'] <= now]
        author_html = author_tmpl.render(author=author, posts=author_posts)
        with open(os.path.join(OUTPUT_DIR, f'author-{author_id}.html'), 'w', encoding='utf-8') as f:
            f.write(author_html)

    # Individual posts
    post_tmpl = env.get_template('post.html')
    for post in filter_posts(posts, before=now):
        post_html = post_tmpl.render(post=post, author=authors.get(post.get('author')), authors=authors)
        with open(os.path.join(OUTPUT_DIR, f"{post['slug']}.html"), 'w', encoding='utf-8') as f:
            f.write(post_html)

    # --- SEARCH INDEX ---
    import json
    search_data = [
        {
            'title': p['title'],
            'summary': p.get('summary', ''),
            'slug': p['slug'],
            'tags': p.get('tags', []),
            'author': p.get('author', ''),
            'date': p['date_obj'].strftime('%Y-%m-%d')
        }
        for p in posts if p['date_obj'] <= now
    ]
    with open(os.path.join(OUTPUT_DIR, 'search.json'), 'w', encoding='utf-8') as f:
        json.dump(search_data, f, indent=2)

    # --- RSS FEED ---
    from generate_rss import generate_rss
    generate_rss(filter_posts(posts, before=now), 'https://yourdomain.com', os.path.join(OUTPUT_DIR, 'rss.xml'))
    print('Site generated in', OUTPUT_DIR)

if __name__ == '__main__':
    render_site()
