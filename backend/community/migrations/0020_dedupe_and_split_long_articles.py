from django.db import migrations


def parse_article_body(body):
    parsed_blocks = []
    paragraph_lines = []

    def flush_paragraph():
        text = "\n".join(paragraph_lines).strip()
        if text:
            parsed_blocks.append(("paragraph", text))
        paragraph_lines.clear()

    for index, raw_line in enumerate(body.splitlines()):
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
    return parsed_blocks


def split_existing_article(ArticleBlock, article):
    body = (article.body or "").strip()
    if not body or "## " not in body:
        return
    text_blocks = list(ArticleBlock.objects.filter(article_id=article.id).exclude(block_type="image"))
    if len(text_blocks) > 1:
        return
    parsed_blocks = parse_article_body(body)
    if not parsed_blocks:
        return

    image_blocks = list(ArticleBlock.objects.filter(article_id=article.id, block_type="image").order_by("position", "id"))
    last_block = ArticleBlock.objects.filter(article_id=article.id).order_by("-position").first()
    temporary_position = max(
        (last_block.position if last_block else 0) + 1,
        len(parsed_blocks) + len(image_blocks) + 1,
    )
    for offset, image_block in enumerate(image_blocks):
        ArticleBlock.objects.filter(id=image_block.id).update(position=temporary_position + offset)
    ArticleBlock.objects.filter(article_id=article.id).exclude(block_type="image").delete()
    ArticleBlock.objects.bulk_create([
        ArticleBlock(article_id=article.id, block_type=block_type, position=position, text=text)
        for position, (block_type, text) in enumerate(parsed_blocks)
    ])
    for offset, image_block in enumerate(image_blocks):
        ArticleBlock.objects.filter(id=image_block.id).update(position=len(parsed_blocks) + offset)


def dedupe_and_backfill_articles(apps, schema_editor):
    Article = apps.get_model("community", "Article")
    ArticleBlock = apps.get_model("community", "ArticleBlock")
    Post = apps.get_model("community", "Post")

    for article in Article.objects.all().iterator():
        split_existing_article(ArticleBlock, article)

    for post in Post.objects.filter(state="published").iterator():
        body = (post.body or "").strip()
        if len(body) < 1000 or body.count("## ") < 3:
            continue
        first_line = body.splitlines()[0].strip() if body.splitlines() else ""
        title = first_line[2:].strip() if first_line.startswith("# ") else post.title
        article = Article.objects.filter(title=title).first() or Article.objects.filter(body=body).first()

        if article is None:
            parsed_blocks = parse_article_body(body)
            summary = next((text[:240] for block_type, text in parsed_blocks if block_type == "paragraph"), "")
            article = Article.objects.create(
                title=title[:180],
                slug=f"promoted-post-{post.id}-v2",
                category="长期用车" if "万公里" in body else "改装案例",
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
        else:
            split_existing_article(ArticleBlock, article)

        post.state = "hidden"
        post.save(update_fields=["state"])


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0019_promote_legacy_long_posts"),
    ]

    operations = [
        migrations.RunPython(dedupe_and_backfill_articles, migrations.RunPython.noop),
    ]
