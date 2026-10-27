# Asset manifest

Stage 3 generates original project-local assets here.

- `mascot-logo.png`: navigation and favicon source, 256x256.
- `mascot-hero.png`: homepage hero, 800x600.
- `mascot-chat.png`: chat avatar, 256x256.
- `mascot-thinking.png`: Agent working state.
- `mascot-celebrate.png`: successful resource/path generation.
- `mascot-empty.png`: empty and gentle guidance state.
- `bg-login.jpg`: authentication split-screen background.
- `bg-hero.jpg`: homepage depth background.
- `document.svg`, `mindmap.svg`, `quiz.svg`, `video.svg`, `code.svg`: local copies of Phosphor regular icons.

The five SVG resource icons come from [Phosphor Icons Core](https://github.com/phosphor-icons/core), MIT license. Stage 4 uses the matching Vue icon package so static and interactive icons remain one family.

Generation provenance and the transparent sprite sheet are retained under `research/assets/stage-3/`. Runtime pages should reference only the named final assets in this directory.
