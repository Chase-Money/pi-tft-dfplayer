# Coding Standards (AI & Devs)

- Python 3.9+, 4-space indent; constants in SCREAMING_SNAKE_CASE.
- Small, single-purpose functions; keep hardware access wrapped in try/except.
- UI: use the v2 framework/components; no new ad-hoc `_v2` forks or monolith expansions.
- Touch: handle ABS/BTN batches, honor calibration/orientation, thresholds configurable (tap ~400ms, drag ~12px, swipe ~70px).
- DFPlayer/backends: avoid side effects in helpers; log and degrade gracefully on UART failures.
- Theming: load via `DFPLAYER_THEME`/`themes/*.json`; no hardcoded palettes where theme is plumbed.
- Git: feature branches only; keep `main` stable; no destructive commands.

## Documentation Organization (December 2025)

**Documentation Consolidation:** As of December 2025, the `/docs` folder has been reorganized to reduce clutter while maintaining comprehensive documentation. Legacy files have been consolidated into 5 focused documents:

### Core Documentation Structure
- **`ARCHITECTURE_AND_DESIGN.md`** - System architecture, design patterns, implementation roadmaps, and future planning
- **`DEVELOPMENT_GUIDE.md`** - Setup instructions, testing strategies, troubleshooting, and maintenance procedures
- **`CHANGELOG_AND_HISTORY.md`** - Version history, project milestones, and development timeline
- **`HARDWARE_INTEGRATION.md`** - Hardware-specific setup, configuration, and integration details
- **`BUGFIXES_AND_MAINTENANCE.md`** - Code quality assessments, bug fixes, test coverage, and maintenance activities

### Documentation Workflow
- **New Documentation:** Add to the appropriate consolidated document based on content type
- **Legacy References:** Old files remain accessible in git history for reference
- **Content Organization:** Use clear headings and maintain chronological ordering where relevant
- **Quality Maintenance:** Keep documentation current, accurate, and well-structured

### Migration Notes
- All historical content has been preserved and consolidated
- Cross-references between documents maintained
- Search functionality improved through better organization
- Documentation quality maintained while reducing file count from 40+ to 5 core documents
