# Changelog

## [0.3.2](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.3.1...v0.3.2) (2024-02-24)


### Bug Fixes

* fix type error in job status checking if sacct fails ([6a197ae](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/6a197ae6d73061def6700af58b29f981dc323278))


### Documentation

* extended docs ([#37](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/37)) ([cf0407c](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/cf0407cc8115d3b64f486b2178b67118e16a12a7))

## [0.3.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.3.0...v0.3.1) (2024-02-14)


### Bug Fixes

* Use sacct syntax that is compatible with slurm &lt; 20.11.0 ([#26](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/26)) ([c1591ff](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/c1591ff0d0eb7267cb5a64906f14e4aa47b9eac7))

## [0.3.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.2.2...v0.3.0) (2024-02-01)


### Features

* print run id to log ([#10](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/10)) ([9ee8291](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/9ee82919ff42886bc5c64480c6fd1f74c4caf0d9))

## [0.2.2](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.2.1...v0.2.2) (2024-02-01)


### Bug Fixes

* Typos in documentation ([#28](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/28)) ([326ce6c](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/326ce6ced3d946ebd485ce80bf03e8e07b1fc717))

## [0.2.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.2.0...v0.2.1) (2024-01-16)


### Bug Fixes

* ensure proper handling of group jobs in combination with the slurm-jobstep executor ([f5c3d4c](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/f5c3d4c6b9bdcba68a512388d36d72d2700920bf))
* remove limitation to single job in jobstep executor for group jobs ([18acfb6](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/18acfb6c4d1588c44941355d0f024c76de52bdbb))

## [0.2.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.1.5...v0.2.0) (2024-01-10)


### Features

* include rule name as comment ([#16](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/16)) ([2e39b18](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/2e39b18688c8e80d4b78c23de01484374a7f065c))

## [0.1.5](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.1.4...v0.1.5) (2024-01-05)


### Bug Fixes

* Force sacct to look at the last 2 days ([#9](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/9)) ([914265d](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/914265df76f1d6eab7ed0b38c61e123489ec0bc2))

## [0.1.4](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.1.3...v0.1.4) (2023-12-08)


### Documentation

* metadata ([4edf9d5](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/4edf9d59f454333299b04f06855bc1522e481d56))

## [0.1.3](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.1.2...v0.1.3) (2023-12-06)


### Bug Fixes

* Handle unresponsive sacct ([#5](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/5)) ([2f7ec1b](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/2f7ec1bb8cc809f0acba92c92819d57fd1affee1))


### Documentation

* update author encoding ([890bdb0](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/890bdb0d011bec922bdce6fa874f06a010ea8334))

## [0.1.2](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.1.1...v0.1.2) (2023-11-20)


### Bug Fixes

* adapt to interface changes ([dcf9bc4](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/dcf9bc434a927a915eebfe9c3e99f13f74407ef5))

## [0.1.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.1.0...v0.1.1) (2023-10-29)


### Bug Fixes

* fix release process ([794bba8](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/794bba86df23ac4d1610f48434e631f0cc43b829))

## 0.1.0 (2023-10-29)


### Bug Fixes

* adapt to API change ([4110331](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/411033198028eb8f894d1327300b5c10ce9618bb))
* adapt to API changes ([75b2383](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/75b2383b914a3dab8e64a68213089b509f322691))
* adapt to API changes in Snakemake 8 ([4c12093](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/4c1209399bfd0ce92fd698447be7fdbd3e526073))
* adapt to changes in snakemake-interface-executor-plugins ([e73f71d](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/e73f71df9e0087afb58f2acd7e71b61b2740a263))
* add dependency on slurm-jobstep ([fb5cdbc](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/fb5cdbc7694144dcb291846810b2b44261fc0a5d))
* update to fixed version of snakemake-interface-executor-plugins ([#2](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/2)) ([3dc72c6](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/3dc72c69a5cbbfd150c21843adb16530c8fa7d34))
