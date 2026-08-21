---
name: release-version
description: Prepare a new release for any project by determining the release scope, updating the version through the project's existing mechanism, writing bilingual Chinese-English release notes in a consistent format, committing the release changes, and drafting WeChat and X/Twitter announcements. Use for requests such as "发布", "发布日志", "发新版本", "开启新版本", "公众号标题", "推文", "release", "changelog", or "release notes" in any repository.
---

# Release Version

Prepare releases consistently across projects without assuming a specific repository layout, version scheme, technology stack, branch name, or release script.

Always consult [git-commit-convention](../git-commit-convention/SKILL.md) before staging or committing. Do not push, create a remote release, publish packages, upload artifacts, or deploy unless the user explicitly requests that external action.

## 1. Discover the Project's Release Conventions

Inspect the repository before changing anything:

- Read project instructions such as `AGENTS.md`, `CLAUDE.md`, contributing guides, and release documentation.
- Inspect recent tags and release-related commits to identify the previous release boundary.
- Locate version declarations, changelogs, existing release notes, bump scripts, build scripts, and CI release workflows.
- Read the most recent release note and preserve useful project-specific metadata, links, and file placement while applying the bilingual format in this skill.
- Derive the repository URL from the Git remote. Derive an official website or download URL from project metadata or existing documentation; never invent one.

Useful discovery commands include:

```bash
git remote -v
git tag --sort=-version:refname
git log --oneline --decorate -50
git log --all --oneline --grep='release\|version\|版本'
```

Use repository-aware search to find likely version files and release tooling. Common locations include `package.json`, `Cargo.toml`, `pyproject.toml`, `*.csproj`, `pom.xml`, `gradle.properties`, application manifests, and scripts containing `bump` or `release`, but do not assume any of them exists.

If the project already has an authoritative release procedure, follow it except where the user explicitly requests this skill's release-note format. If multiple version declarations are expected to stay synchronized, update all of them through the existing project script when available.

## 2. Determine the Release Scope

Choose the most reliable previous-release boundary in this order:

1. The latest reachable release tag.
2. The previous release commit identified by the project's established commit pattern.
3. The version recorded by an existing changelog or release-note index.

Review every commit and relevant diff from that boundary through `HEAD`. Include working-tree changes only when the user explicitly intends them to be part of the release.

Group changes by user-facing theme rather than mirroring the commit list. Distinguish:

- New capabilities and meaningful improvements.
- User-visible fixes and compatibility changes.
- Breaking changes, migrations, deprecations, and known limitations.
- Engineering-only work such as refactors, CI maintenance, dependency housekeeping, or documentation infrastructure.

Omit engineering-only work from the main user-facing notes. Include it under a separate `工程改进 | Engineering Improvements` section only when it is important to operators or the user asks for it.

Do not claim a change unless the commit history or diff supports it. Call out ambiguous scope, inconsistent versions, or missing release boundaries before committing.

## 3. Update the Version

Use the version requested by the user. When no version is specified, infer the next version only if the repository has an unambiguous versioning convention; otherwise ask the user for the target version.

Prefer the project's existing version-bump script or package-manager command. If none exists, update only authoritative version files established by the repository. Preserve the project's version syntax, including whether filenames, frontmatter, and display text use a leading `v`.

After updating, verify that all synchronized version declarations agree and review the resulting diff. Run any release-specific validation provided by the project.

## 4. Write the Release Notes

Write the note in the project's existing release-note directory. If the repository has no convention, use `docs/releases/<version>.md` and create only the directories needed for that file.

Use the following structure. Chinese comes first and its English counterpart immediately follows. Adapt optional metadata to facts available in the repository, but keep the overall order.

```markdown
---
title: <version>
---

<One Chinese paragraph summarizing the release theme. Bold the headline features.>

<The equivalent English paragraph.>

---

## 版本信息 | Release Information

- **项目地址 | Repository**：<repository URL>
- **官方网站 | Official Website**：<official website, if the project has one>
- **版本号 | Version**：<display version>
- **发布日期 | Release Date**：<YYYY年M月D日> | <Month D, YYYY>

---

## <中文主题> | <English Theme>

- <Chinese user-facing change>
- <Chinese user-facing change>

- <Equivalent English change>
- <Equivalent English change>

---

## 立即下载 | Download Now

在 [GitHub Releases](<release URL>) 下载最新版本，或访问[官方网站](<official website>)了解更多信息。

Download the latest version from [GitHub Releases](<release URL>), or visit the [Official Website](<official website>) for more information.
```

When no official website exists, omit that metadata row and remove the website clause from both download sentences. When the project is not hosted on GitHub, use its actual release or download page and adjust the link label without changing the bilingual structure.

Release-note requirements:

- Use a small number of plain-text thematic sections appropriate to the actual changes.
- Lead with the most impactful user-facing features and bold the headline features in the summaries.
- Keep Chinese and English semantically equivalent; do not add claims in only one language.
- Use concrete product language understandable without reading commits or source code.
- Explain breaking changes and required migrations prominently.
- Do not use emoji anywhere in release notes or announcement copy.
- Use a real date obtained from the environment. Format it as `2026年6月29日 | June 29, 2026`.
- Do not invent repository, website, download, issue, or documentation URLs.

If the project uses a release-note index or navigation file that is not generated automatically, update it. Verify whether this is necessary instead of assuming either behavior.

## 5. Validate and Commit

Before committing:

1. Review the complete release diff and confirm the version, date, links, and scope.
2. Run the repository's required pre-commit and release checks in proportion to the changed files.
3. Confirm that generated lockfiles or manifests expected from the version bump are included.
4. Stage only the files belonging to this release.

Use the repository's established release commit style. If no established pattern exists, use an English Conventional Commit message such as:

```text
docs(release): add <version> release notes
```

If the version bump and release note are normally committed separately, preserve that history pattern. Otherwise keep them in one atomic release-preparation commit when they form a single project convention.

Stop after the local commit by default. Report the commit hash and any external actions still required. Never push solely because the user said "release"; pushing, tagging, creating a hosted release, publishing packages, uploading artifacts, and deploying each require explicit user authorization or an already explicit request covering that action.

## 6. Open the Next Development Cycle

Only open a new development cycle when the user asks for it.

- Determine the next development version from the project's established version scheme.
- Use the repository's existing bump mechanism.
- Follow its current branch naming convention rather than imposing names such as `dev-<version>`.
- Commit the new-cycle bump using the project's established message pattern.
- Do not push the commit or branch unless explicitly requested.

If no next-version or branch convention can be established reliably, ask the user instead of inventing one.

## 7. Draft Announcement Copy

When requested, provide both formats:

### 公众号标题

Provide two or three concise Chinese title options, with the recommended option first. Emphasize the release's strongest user benefit rather than merely stating the version number.

### X / Twitter

Write concise English copy containing:

- The version and release theme.
- A short list of the most important user-facing highlights.
- The verified release or repository URL.

Do not use emoji, unsupported claims, internal engineering details, or invented links.
