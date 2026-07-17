from django.db import migrations


def promote_legacy_long_posts(apps, schema_editor):
    Article = apps.get_model("community", "Article")
    ArticleBlock = apps.get_model("community", "ArticleBlock")
    Post = apps.get_model("community", "Post")

    for post in Post.objects.filter(state="published").iterator():
        body = (post.body or "").strip()
        if len(body) < 1000 or body.count("## ") < 3:
            continue

        lines = body.splitlines()
        first_line = lines[0].strip() if lines else ""
        title = first_line[2:].strip() if first_line.startswith("# ") else post.title
        slug = f"promoted-post-{post.id}"
        if Article.objects.filter(slug=slug).exists():
            post.state = "hidden"
            post.save(update_fields=["state"])
            continue

        parsed_blocks = []
        paragraph_lines = []

        def flush_paragraph():
            text = "\n".join(paragraph_lines).strip()
            if text:
                parsed_blocks.append(("paragraph", text))
            paragraph_lines.clear()

        for index, raw_line in enumerate(lines):
            line = raw_line.strip()
            if index == 0 and line.startswith("# "):
                continue
            if line.startswith("## "):
                flush_paragraph()
                parsed_blocks.append(("heading", line[3:].strip()))
            elif not line:
                flush_paragraph()
            else:
                paragraph_lines.append(raw_line.strip())
        flush_paragraph()

        summary = next((text[:240] for block_type, text in parsed_blocks if block_type == "paragraph"), "")
        category = "长期用车" if "万公里" in body else "改装案例"
        article = Article.objects.create(
            title=title[:180],
            slug=slug,
            category=category,
            summary=summary,
            body=body,
            image=post.image,
            image_upload=post.image_upload.name if post.image_upload else "",
            image_caption=post.image_caption,
            owner_id=post.owner_id,
            author=post.author,
            car_id=post.car_id,
            is_pinned=post.is_pinned,
            featured=post.featured,
            state="published",
        )
        Article.objects.filter(id=article.id).update(created_at=post.created_at, updated_at=post.updated_at)
        ArticleBlock.objects.bulk_create([
            ArticleBlock(article_id=article.id, block_type=block_type, position=position, text=text)
            for position, (block_type, text) in enumerate(parsed_blocks)
        ])
        post.state = "hidden"
        post.save(update_fields=["state"])


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0018_article_comments_article_likes_article_owner_and_more"),
    ]

    operations = [
        migrations.RunPython(promote_legacy_long_posts, migrations.RunPython.noop),
    ]
