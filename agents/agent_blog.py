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
        # Sans ça, le 301 de gql.hashnode.com est suivi jusqu'à une page web et
        # resp.json() lève « Expecting value: line 1 column 1 » — l'erreur qui
        # masquait le vrai problème dans les logs.
        allow_redirects=False,
    )

    if resp.is_redirect or "json" not in (resp.headers.get("content-type") or ""):
        raise RuntimeError(
            "L'API GraphQL Hashnode n'est plus accessible : elle a été réservée "
            "aux publications Pro. L'endpoint redirige vers la page d'annonce "
            "au lieu de répondre. Voir https://hashnode.com/announcements/graphql-api"
        )

    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"Hashnode : {data['errors']}")

    post_url = data["data"]["publishPost"]["post"]["url"]
    print(f"  [agent_blog] ✓ Article publié : {post_url}")
    return post_url
