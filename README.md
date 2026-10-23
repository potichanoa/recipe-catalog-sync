# Pinterest Recipe Catalog Sync

This repository contains a personal tool to export Pins from the owner's private Pinterest Food board into a CSV and JSON catalog.

## GitHub Actions setup

1. Open **Settings → Secrets and variables → Actions** in this repository.
2. Add a repository secret named **`PINTEREST_ACCESS_TOKEN`** containing the current Pinterest access token.
3. Open **Actions → Sync Pinterest Recipe Catalog → Run workflow** to run the first sync.
4. When the run finishes, open it and download the `pinterest-recipe-catalog` artifact.

The workflow also runs daily. It does not commit the catalog to this public repository; the generated files are uploaded as workflow artifacts and expire after 30 days.

## Important token note

Pinterest access tokens expire. This first version uses the access token supplied as a GitHub secret and will stop with a clear error if it expires. Fully unattended long-term syncing also needs secure refresh-token rotation/storage; do not paste tokens into source files, issues, or chat. The repository is public, so never commit token values or generated private-board data.
