"""Compatibility entry point: migrate DCS core and all resource directories."""
from migrate_dcs_complete import CATEGORIES, categories_for, digest, main, mislabeled_audio

if __name__ == "__main__":
    raise SystemExit(main())
