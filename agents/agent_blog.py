"""
Agent — Publication sur Hashnode via GraphQL API.
"""
import requests
from config import HASHNODE_TOKEN, HASHNODE_PUBLICATION_ID

_GQL = "https://gql.hashnode.com"


def publish_to_hashnode(
    article: dict,
    cover_url: str | None = None,
) -> str:
    """
    Publie l'article sur Hashnode.

    Args:
        article:   dict avec title, author, body, slug
        cover_url: URL publique de la couverture (Cloudinary)

    Returns:
        URL de l'article publié
    """
    title    = f"{article['title']} — {article['author']}"
    markdown = article["body"]

    inp = {
        "title":           title,
        "publicationId":   HASHNODE_PUBLICATION_ID,
        "contentMarkdown": markdown,
        "slug":            article.get("slug", ""),
        "tags":            [],
    }
    if cover_url:
        inp["coverImageOptions"] = {"coverImageURL": cover_url}

    query = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) {
        post { id slug url title }
      }
    }
    """
    resp = requests.post(
        _GQL,
        json={"query": query, "variables": {"input": inp}},
        headers={
            "Authorization": HASHNODE_TOKEN,
            "Content-Type":  "application/json",
        },
        timeout=30,
    )
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"Hashnode : {data['errors']}")

    post_url = data["data"]["publishPost"]["post"]["url"]
    print(f"  [agent_blog] ✓ Article publié : {post_url}")
    return post_url
