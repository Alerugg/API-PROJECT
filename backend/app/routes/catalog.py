from flask import Blueprint, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import db

catalog_bp = Blueprint("catalog", __name__)

_RATE_LIMIT_BUCKETS = {}
_CACHE = {}


def _int_param(name: str, default: int, maximum: int) -> int:
    value = request.args.get(name, default=default, type=int)
    if value is None:
        return default
    return min(max(value, 0), maximum)


def _json_error(error: str, detail: str, status: int):
    return jsonify({"error": error, "detail": detail}), status


@catalog_bp.get("/api/cards")
@catalog_bp.get("/api/v1/cards")
def list_cards():
    q = request.args.get("q", "").strip()
    game = request.args.get("game", "").strip()
    limit = _int_param("limit", 20, 100)
    offset = _int_param("offset", 0, 100000)

    where = []
    params = {"limit": limit, "offset": offset}
    if game:
        where.append("g.slug = :game")
        params["game"] = game
    if q:
        where.append("LOWER(c.name) LIKE :q")
        params["q"] = f"%{q.lower()}%"

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    sql = text(
        f"""
        SELECT c.id, c.name, g.slug AS game
        FROM cards c
        JOIN games g ON g.id = c.game_id
        {where_sql}
        ORDER BY c.name, c.id
        LIMIT :limit OFFSET :offset
        """
    )

    with db.SessionLocal() as session:
        rows = session.execute(sql, params).mappings().all()
    result = [dict(row) for row in rows]
    return jsonify(result)


@catalog_bp.get("/api/sets")
@catalog_bp.get("/api/v1/sets")
def list_sets():
    game = request.args.get("game", "").strip()
    q = request.args.get("q", "").strip()
    order = (request.args.get("order") or "release_date_desc").strip().lower()
    limit = _int_param("limit", 50, 200)
    offset = _int_param("offset", 0, 100000)

    if q and len(q) < 2:
        return _json_error("invalid_params", "q must have at least 2 characters", 400)

    order_clause = {
        "release_date_desc": "s.release_date DESC NULLS LAST, s.name ASC",
        "release_date_asc": "s.release_date ASC NULLS LAST, s.name ASC",
        "name_asc": "s.name ASC, s.id ASC",
        "name_desc": "s.name DESC, s.id DESC",
    }.get(order, "s.release_date DESC NULLS LAST, s.name ASC")

    where = []
    params = {"limit": limit, "offset": offset}

    if game:
        where.append("g.slug = :game")
        params["game"] = game
    if q:
        where.append("(LOWER(s.name) LIKE :q OR LOWER(s.code) LIKE :q)")
        params["q"] = f"%{q.lower()}%"

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    sql = text(
        f"""
        SELECT s.id,
               g.slug AS game,
               s.code,
               s.name,
               s.release_date
        FROM sets s
        JOIN games g ON g.id = s.game_id
        {where_sql}
        ORDER BY {order_clause}
        LIMIT :limit OFFSET :offset
        """
    )

    try:
        with db.SessionLocal() as session:
            rows = session.execute(sql, params).mappings().all()
    except SQLAlchemyError as error:
        return _json_error("sets_query_failed", str(error), 500)

    return jsonify([dict(row) for row in rows])


@catalog_bp.get("/api/prints")
@catalog_bp.get("/api/v1/prints")
def list_prints():
    q = request.args.get("q", "").strip()
    game = request.args.get("game", "").strip()
    limit = _int_param("limit", 20, 100)
    offset = _int_param("offset", 0, 100000)

    where = []
    params = {"limit": limit, "offset": offset}
    if game:
        where.append("g.slug = :game")
        params["game"] = game
    if q:
        where.append("(LOWER(c.name) LIKE :q OR LOWER(p.collector_number) LIKE :q)")
        params["q"] = f"%{q.lower()}%"

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    sql = text(
        f"""
        SELECT p.id, c.name AS card_name, s.code AS set_code, p.collector_number
        FROM prints p
        JOIN cards c ON c.id = p.card_id
        JOIN sets s ON s.id = p.set_id
        JOIN games g ON g.id = s.game_id
        {where_sql}
        ORDER BY s.code, p.collector_number, p.id
        LIMIT :limit OFFSET :offset
        """
    )

    with db.SessionLocal() as session:
        rows = session.execute(sql, params).mappings().all()
    result = [dict(row) for row in rows]
    return jsonify(result)


@catalog_bp.get("/api/products")
@catalog_bp.get("/api/v1/products")
def list_products():
    game = request.args.get("game", "").strip()
    set_code = request.args.get("set_code", "").strip()
    product_type = request.args.get("type", "").strip()
    q = request.args.get("q", "").strip()
    limit = _int_param("limit", 20, 100)
    offset = _int_param("offset", 0, 100000)

    where = []
    params = {"limit": limit, "offset": offset}
    if game:
        where.append("g.slug = :game")
        params["game"] = game
    if set_code:
        where.append("s.code = :set_code")
        params["set_code"] = set_code
    if product_type:
        where.append("p.product_type = :product_type")
        params["product_type"] = product_type
    if q:
        where.append("LOWER(p.name) LIKE :q")
        params["q"] = f"%{q.lower()}%"

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    sql = text(
        f"""
        SELECT p.id,
               g.slug AS game,
               s.code AS set_code,
               p.product_type,
               p.name,
               p.release_date,
               COALESCE(v.variant_count, 0) AS variant_count,
               i.primary_image_url
        FROM products p
        JOIN games g ON g.id = p.game_id
        LEFT JOIN sets s ON s.id = p.set_id
        LEFT JOIN (
            SELECT product_id, COUNT(*) AS variant_count
            FROM product_variants
            GROUP BY product_id
        ) v ON v.product_id = p.id
        LEFT JOIN (
            SELECT pv.product_id, MIN(pi.url) AS primary_image_url
            FROM product_variants pv
            JOIN product_images pi ON pi.product_variant_id = pv.id
            WHERE pi.is_primary = true
            GROUP BY pv.product_id
        ) i ON i.product_id = p.id
        {where_sql}
        ORDER BY p.name ASC, p.id ASC
        LIMIT :limit OFFSET :offset
        """
    )
    count_sql = text(
        f"""
        SELECT COUNT(*)
        FROM products p
        JOIN games g ON g.id = p.game_id
        LEFT JOIN sets s ON s.id = p.set_id
        {where_sql}
        """
    )

    try:
        with db.SessionLocal() as session:
            rows = session.execute(sql, params).mappings().all()
            total = session.execute(count_sql, params).scalar_one()
    except SQLAlchemyError as error:
        return _json_error("products_query_failed", str(error), 500)

    items = []
    for row in rows:
        item = dict(row)
        if hasattr(item.get("release_date"), "isoformat"):
            item["release_date"] = item["release_date"].isoformat()
        items.append(item)

    return jsonify({"items": items, "limit": limit, "offset": offset, "total": total})


@catalog_bp.get("/api/products/<int:product_id>")
@catalog_bp.get("/api/v1/products/<int:product_id>")
def product_detail(product_id: int):
    product_sql = text(
        """
        SELECT p.id,
               g.slug AS game,
               s.code AS set_code,
               p.product_type,
               p.name,
               p.release_date
        FROM products p
        JOIN games g ON g.id = p.game_id
        LEFT JOIN sets s ON s.id = p.set_id
        WHERE p.id = :product_id
        """
    )
    variants_sql = text(
        """
        SELECT id, product_id, language, region, packaging, sku
        FROM product_variants
        WHERE product_id = :product_id
        ORDER BY id ASC
        """
    )
    images_sql = text(
        """
        SELECT pi.id, pi.product_variant_id, pi.url, pi.is_primary, pi.source
        FROM product_images pi
        JOIN product_variants pv ON pv.id = pi.product_variant_id
        WHERE pv.product_id = :product_id
        ORDER BY pi.product_variant_id ASC, pi.is_primary DESC, pi.id ASC
        """
    )
    identifiers_sql = text(
        """
        SELECT pid.id, pid.product_variant_id, pid.source, pid.external_id
        FROM product_identifiers pid
        JOIN product_variants pv ON pv.id = pid.product_variant_id
        WHERE pv.product_id = :product_id
        ORDER BY pid.product_variant_id ASC, pid.source ASC, pid.id ASC
        """
    )

    try:
        with db.SessionLocal() as session:
            product = session.execute(product_sql, {"product_id": product_id}).mappings().first()
            if product is None:
                return _json_error("not_found", f"product {product_id} not found", 404)
            variants = session.execute(variants_sql, {"product_id": product_id}).mappings().all()
            images = session.execute(images_sql, {"product_id": product_id}).mappings().all()
            identifiers = session.execute(identifiers_sql, {"product_id": product_id}).mappings().all()
    except SQLAlchemyError as error:
        return _json_error("product_detail_failed", str(error), 500)

    product_payload = dict(product)
    if hasattr(product_payload.get("release_date"), "isoformat"):
        product_payload["release_date"] = product_payload["release_date"].isoformat()

    return jsonify(
        {
            "product": product_payload,
            "variants": [dict(row) for row in variants],
            "images": [dict(row) for row in images],
            "identifiers": [dict(row) for row in identifiers],
        }
    )


@catalog_bp.get("/api/product-variants")
@catalog_bp.get("/api/v1/product-variants")
def list_product_variants():
    product_id = request.args.get("product_id", type=int)
    if product_id is None:
        return _json_error("invalid_params", "product_id is required", 400)

    sql = text(
        """
        SELECT id, product_id, language, region, packaging, sku
        FROM product_variants
        WHERE product_id = :product_id
        ORDER BY id ASC
        """
    )

    with db.SessionLocal() as session:
        rows = session.execute(sql, {"product_id": product_id}).mappings().all()

    return jsonify([dict(row) for row in rows])


@catalog_bp.get("/api/prints/<int:print_id>")
@catalog_bp.get("/api/v1/prints/<int:print_id>")
def get_print_detail(print_id: int):
    sql = text(
        """
        SELECT p.id,
               p.collector_number,
               p.language,
               p.rarity,
               p.is_foil,
               c.id AS card_id,
               c.name AS card_name,
               s.id AS set_id,
               s.code AS set_code,
               s.name AS set_name,
               s.release_date
        FROM prints p
        JOIN cards c ON c.id = p.card_id
        JOIN sets s ON s.id = p.set_id
        WHERE p.id = :print_id
        """
    )
    images_sql = text(
        """
        SELECT url, is_primary, source
        FROM print_images
        WHERE print_id = :print_id
        ORDER BY is_primary DESC, id ASC
        """
    )
    identifiers_sql = text(
        """
        SELECT source, external_id
        FROM print_identifiers
        WHERE print_id = :print_id
        ORDER BY source ASC, id ASC
        """
    )

    try:
        with db.SessionLocal() as session:
            row = session.execute(sql, {"print_id": print_id}).mappings().first()
            if row is None:
                return _json_error("not_found", f"print {print_id} not found", 404)
            images = session.execute(images_sql, {"print_id": print_id}).mappings().all()
            identifiers = session.execute(identifiers_sql, {"print_id": print_id}).mappings().all()
    except SQLAlchemyError as error:
        return _json_error("print_detail_failed", str(error), 500)

    return jsonify(
        {
            "print": {
                "id": row["id"],
                "collector_number": row["collector_number"],
                "language": row["language"],
                "rarity": row["rarity"],
                "is_foil": row["is_foil"],
            },
            "card": {"id": row["card_id"], "name": row["card_name"]},
            "set": {
                "id": row["set_id"],
                "code": row["set_code"],
                "name": row["set_name"],
                "release_date": row["release_date"].isoformat() if hasattr(row["release_date"], "isoformat") else row["release_date"],
            },
            "images": [dict(image) for image in images],
            "identifiers": [dict(identifier) for identifier in identifiers],
        }
    )
