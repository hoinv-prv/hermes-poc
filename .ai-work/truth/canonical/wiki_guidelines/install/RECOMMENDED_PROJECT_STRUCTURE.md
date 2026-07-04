# RECOMMENDED_PROJECT_STRUCTURE_v0_5_0

## Recommended structure
```text
project-root/
  aiws/
    wiki/
      package/
        core/
          specs/
          guidelines/
          prompts/
        rollout/
        upgrade/
        appendix/
      project-local/
        project_profile/
        mapping_patterns/
        meta_build_outputs/
        aip_customizations/
        rollout_notes/
        reference/                # curated project-local reference docs (e.g. document_search_guidelines.md)
```

## Notes
- `package/` giữ bộ canonical install package
- `project-local/` giữ phần project-specific và outputs sinh ra sau khi áp dụng package
- không nên trộn lẫn project-local files vào canonical package files
- `reference/` giữ project-local reference docs (curated reading guides). Bắt buộc có `document_search_guidelines.md` (scaffold từ `install/document_search_guidelines.template.md`) — xem `INSTALL_CHECKLIST.md`. Trong runtime tree hiện hành, path là `.ai-work/wiki/reference/document_search_guidelines.md`.
