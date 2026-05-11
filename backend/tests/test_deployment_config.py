from pathlib import Path
import json


def test_render_blueprint_captures_public_beta_runtime_contract():
    blueprint = Path(__file__).resolve().parents[2] / "render.yaml"
    text = blueprint.read_text(encoding="utf-8")

    assert "name: sigmalite-api" in text
    assert "runtime: python" in text
    assert "healthCheckPath: /health/ready" in text
    assert "alembic upgrade head" in text
    assert "uvicorn app.main:app --host 0.0.0.0 --port $PORT" in text
    assert "name: sigmalite-postgres" in text
    assert "name: sigmalite-redis" in text
    assert "RATE_LIMIT_BACKEND" in text
    assert "value: redis" in text
    assert "ALLOWED_ORIGINS" in text
    assert "sync: false" in text


def test_vercel_config_rewrites_spa_routes():
    config_path = Path(__file__).resolve().parents[2] / "frontend" / "vercel.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert config["buildCommand"] == "npm run build"
    assert config["outputDirectory"] == "dist"
    assert {"source": "/(.*)", "destination": "/index.html"} in config["rewrites"]
