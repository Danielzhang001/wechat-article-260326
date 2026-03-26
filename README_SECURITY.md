# Public Share Notes

This package is sanitized for public GitHub sharing.

## Included
- Core scripts and docs
- Example config templates under `data/`

## Removed
- Real credentials (`data/wechat_config.json`, `data/unsplash_config.json`, profile secrets)
- Runtime artifacts (`output/`, `articles/`, `images/`, `.venv/`)

## Before first run
1. Copy `data/wechat_config.example.json` to `data/wechat_config.json` and fill real values.
2. Copy `data/unsplash_config.example.json` to `data/unsplash_config.json` and fill real values.
3. Never commit real config files to a public repository.
