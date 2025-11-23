# Refactoring and Unification Plan for pi-tft-dfplayer

## 1. Overview and Goal

This document outlines the plan to refactor the `pi-tft-dfplayer` codebase. The primary goal is to resolve the architectural issues stemming from an incomplete refactoring effort, resulting in a single, maintainable, and modular application.

**Source of truth for agents/devs:** All current guidance (architecture, standards, logs) lives under `docs/ai/`:
- `docs/ai/PROJECT_GUIDE.md` – read first for architecture direction and workflow
- `docs/ai/CODING_STANDARDS.md` – coding rules/patterns
- `docs/ai/TASK_LOG.md` – optional running log

The current codebase is difficult to maintain due to two main factors:
- **A Monolithic Core:** The main application logic resides in `src/dfplayer_fb_gui.py`, which handles UI rendering, event handling, and state management in one large file.
- **Code Duplication:** A parallel, partially implemented `v2` architecture exists in numerous `*_v2.py` files. This creates confusion, duplicates effort, and makes it unclear which implementation is canonical.

The end goal is a unified architecture that is easy to understand, extend, and debug.

## 2. Target Architecture

We will evolve the application to a modular, state-driven architecture with a clear separation of concerns:

- **Main Application (`src/main.py`):** A single, clear entry point responsible for initializing the system and running the main application loop.
- **State Management (`src/core/state.py`):** A centralized class to manage the application's state (e.g., current track, volume, playback status). UI components will react to changes in this state.
- **Configuration (`src/core/config.py`):** A unified configuration manager for loading and accessing settings.
- **UI Framework (`src/ui/`):** A component-based UI system built upon the `v2` renderer.
    - **Renderer:** A low-level drawing engine.
    - **Framework:** A system for defining and managing UI components, views, and their lifecycle.
    - **Views/Screens:** High-level components representing different application screens (e.g., "Now Playing", "Track List").
- **Hardware Abstractions (`src/hardware/`):** Modules that provide a clean API for interacting with physical components (Display, Touch Controller, DFPlayer).
- **Backend Services (`src/backends/`):** Logic for audio playback and metadata management, decoupled from the UI.

## 3. Step-by-Step Execution Plan

This refactoring is broken down into four phases.

### Phase 1: Consolidate Core Components

The first step is to unify the core configuration and state management systems by adopting the improved `v2` implementations.

1.  **Analyze `_v2` files:** Identify all `*_v2.py` files to understand the full scope of the duplicated code.
2.  **Integrate `config_v2.py`:** Merge the logic from `src/core/config_v2.py` into `src/core/config.py`. The goal is a single, robust configuration class that reads from `~/.dfplayer_config.json`.
3.  **Integrate `state_v2.py`:** Replace the simple dictionary-based state in the main application with the more structured class from `src/core/state_v2.py`. This new state manager will be the single source of truth for the application's state.
4.  **Create New Entry Point:** Create a new `src/main.py` file that will serve as the entry point for the refactored application.

### Phase 2: Implement the UI Framework

With the core in place, the next phase is to build out the UI foundation.

1.  **Consolidate UI Renderer:** Move the `renderer_v2` code into a finalized location, e.g., `src/ui/renderer.py`.
2.  **Consolidate UI Framework:** Formalize the `framework_v2` code into a coherent framework in `src/ui/framework/`. This framework should provide base classes for views, components, and event handling.
3.  **Define Base Screens:** Create the basic screen templates (e.g., `NowPlayingScreen`, `MenuListScreen`) using the new framework. Initially, these can be simple placeholders.

### Phase 3: Migrate Application Logic

This is the most intensive phase, involving the careful deconstruction of `dfplayer_fb_gui.py`.

1.  **Deconstruct the Monolith:** Go through `dfplayer_fb_gui.py` section by section (e.g., drawing logic, touch handling, DFPlayer commands).
2.  **Migrate UI Logic:** Re-implement the UI elements (buttons, text labels, album art) as components within the new UI framework. Place this logic inside the new screen classes.
3.  **Migrate Event Handling:** Connect touch events from the hardware layer to the UI framework's event system. UI components should handle their own touch events.
4.  **Migrate Backend Logic:** Ensure all audio playback commands are routed through the `DFPlayerBackend`, which interacts with the `state` manager.

### Phase 4: Cleanup and Documentation

The final phase is to remove all obsolete code and update the project documentation.

1.  **Delete `_v2` files:** Systematically delete all `*_v2.py` and other temporary files that have been successfully replaced.
2.  **Delete `dfplayer_fb_gui.py`:** Once all its logic has been migrated, the original monolithic file can be removed.
3.  **Run Tests:** Execute the project's test suite (`pytest`) to verify that the refactored application maintains all original functionality.
4.  **Update Documentation:**
    -   Modify `README.md` to update the "Running the Application" section to use `src/main.py`.
    -   Add a new section on the project's architecture.
    -   Explicitly deprecate the "v2 file versioning policy" mentioned in `GEMINI.md` and state that all changes should be managed through Git branches.

## 4. New Development Guidelines

- **No More `_v2` Files:** All new features or fixes must be developed within the unified architecture. The practice of creating versioned copies of files is officially deprecated.
- **Use Git Branches:** All development work should be done in feature branches. The `main` branch should be kept stable.
- **Follow the Architecture:** New UI elements should be created as components within the UI framework. New logic should be placed in the appropriate service or state management layer.

**Current entrypoint**: `src/main.py` (app_v2 + ConfigV2 + ScreenManagerV2). Older entrypoints such as `main_v2.py` and `main_touch_v2.py` are legacy/compatibility only.

By following this plan, we will create a robust and maintainable foundation for the future of the `pi-tft-dfplayer` project.
