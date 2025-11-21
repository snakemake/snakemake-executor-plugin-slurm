# Changelog

## [1.9.2](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.9.1...v1.9.2) (2025-10-28)


### Bug Fixes

* logo ([#367](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/367)) ([3781f36](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/3781f36567c2ede2a176819af66073601203a2c0))

## [1.9.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.9.0...v1.9.1) (2025-10-27)


### Bug Fixes

* logo path ([#365](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/365)) ([a2bd944](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/a2bd944a46110308e5afdc3af9fecbc8c75c0b80))

## [1.9.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.8.0...v1.9.0) (2025-10-27)


### Features

* preventing overwrites ([#358](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/358)) ([799f95b](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/799f95b21f36b58df8595d13f90f9fcfb02dad3d))


### Bug Fixes

* mpi task settings ([#363](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/363)) ([7f0742a](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/7f0742a8f242ecfd57f807830ce9824f3de8e574))
* time conversion for efficiency reports with jobs taking longer than 1 day ([#362](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/362)) ([ba263ce](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/ba263ce300a0f534b007642c6c4fe29c26aa600f))

## [1.8.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.7.0...v1.8.0) (2025-09-18)


### Features

* adding image for mastodon posts ([#349](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/349)) ([b27168c](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/b27168ccadc5c259dd09dd13cce3a06cd7b78238))


### Bug Fixes

* account lookup / test in multicluster environment ([#350](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/350)) ([d6759d0](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/d6759d09ad3608c261556f49ef5c7372ef20e1a1))
* quoting parameters ([#355](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/355)) ([660c800](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/660c8000fa3db9a4b90e2d36d17c66f3c56b79ed))

## [1.7.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.6.1...v1.7.0) (2025-09-09)


### Features

* new flag for SLURM qos ([#351](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/351)) ([55068ae](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/55068ae6a47c61b38487110f59eaa6da13e4c051))

## [1.6.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.6.0...v1.6.1) (2025-08-21)


### Bug Fixes

* efficiency report jobsteps ([#338](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/338)) ([a4cbe36](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/a4cbe368bd4d2bfc6461b59be3b00f3c1c7e327b))
* gpu tasks are unset if &lt;= 0 ([#347](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/347)) ([564e0f7](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/564e0f775a373fb1c44fa06f0f974af54615f892))
* updated poetry ([#343](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/343)) ([58d471d](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/58d471db0d15b264a0167df7ebc6e5e8216063b1))


### Documentation

* added notes about ntasks per gpu ([#346](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/346)) ([adcd86e](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/adcd86e5ce1c9eaf1ad75d2004eafbd21a2670fd))

## [1.6.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.5.0...v1.6.0) (2025-07-22)


### Features

* added github action to label long pending issues as 'stale' ([#239](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/239)) ([6d7c50a](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/6d7c50ae492c9557b6cc39119c572c5b5ef1b341))
* treat sbatch errors as job errors instead of workflow errors ([#322](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/322)) ([5e38507](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/5e3850762c73abf1fff8ba9e1e8c18379251041f))
* using the current version of the announcement bot for Mastodon  ([#333](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/333)) ([03e0e24](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/03e0e2426edbe2957be93f02f3ae3834f710faff))


### Bug Fixes

* allow unsetting of tasks for gpu jobs ([#318](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/318)) ([53ac8b0](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/53ac8b09a78213dd552216a05eb43dcc3444706c))

## [1.5.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.4.0...v1.5.0) (2025-07-04)


### Features

* measuring compute efficiency per job ([#221](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/221)) ([3cef6b7](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/3cef6b7889c8ba09280f345bade3497b144bedc7))

## [1.4.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.3.6...v1.4.0) (2025-06-12)


### Features

* adding reservation flag ([#323](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/323)) ([d4e0a0f](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/d4e0a0f4160f5336c5bf36be8f097b8a01f77718))


### Documentation

* review and edit new docs ([#237](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/237)) ([ec82a70](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/ec82a70b95652afcbc21d44a4dbca14d78dc8936))

## [1.3.6](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.3.5...v1.3.6) (2025-05-18)


### Bug Fixes

* release notes to action script ([#310](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/310)) ([c5a3d6e](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/c5a3d6ebcc8493731b4e3a048a603eb110847de4))

## [1.3.5](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.3.4...v1.3.5) (2025-05-17)


### Bug Fixes

* full release notes ([#308](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/308)) ([736b452](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/736b4528d95d5473534522eecbea64f71023885a))

## [1.3.4](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.3.3...v1.3.4) (2025-05-17)


### Bug Fixes

* full release notes ([#306](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/306)) ([f4a8277](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/f4a827747b3e86590746907d16151605f705455a))

## [1.3.3](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.3.2...v1.3.3) (2025-05-17)


### Bug Fixes

* full release notes ([#304](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/304)) ([0465f85](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/0465f85c5d0fd34fce6ef650220890533059a2dd))

## [1.3.2](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.3.1...v1.3.2) (2025-05-17)


### Bug Fixes

* full release notes ([#302](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/302)) ([7fd32f0](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/7fd32f0f4a22b5f54fedaab0282242244fb35d9a))

## [1.3.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.3.0...v1.3.1) (2025-05-17)


### Bug Fixes

* full release notes ([#300](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/300)) ([4faed8d](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/4faed8d3729934174281bc08baa33bd0c0b4537f))

## [1.3.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.17...v1.3.0) (2025-05-17)


### Features

* attempt to gain full release notes posted on mastodon ([#298](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/298)) ([b207279](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/b2072798961723ded86ac002b5bc606bd114a780))

## [1.2.17](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.16...v1.2.17) (2025-05-16)


### Bug Fixes

* tolerant argparsing for mastodon announcements ([#296](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/296)) ([3b4fbe0](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/3b4fbe0db352bd56af5df8bb669879dbd28b7264))

## [1.2.16](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.15...v1.2.16) (2025-05-16)


### Bug Fixes

* announce action ([#294](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/294)) ([7906f0c](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/7906f0c07de6033f0d95e795efbfacaa131de793))

## [1.2.15](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.14...v1.2.15) (2025-05-16)


### Bug Fixes

* announce action ([#291](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/291)) ([6dd4053](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/6dd4053ce7e2cb1f12f289b5fbfe83a1b50832d9))

## [1.2.14](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.13...v1.2.14) (2025-05-16)


### Bug Fixes

* new version announcement bot ([#289](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/289)) ([732e3d4](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/732e3d46e69b198a97785fb04add197c2afde1ec))

## [1.2.13](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.12...v1.2.13) (2025-05-16)


### Bug Fixes

* pr title ([#287](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/287)) ([a3a548c](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/a3a548c85229f7b301c6f9597e25b78d1abd77e4))

## [1.2.12](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.11...v1.2.12) (2025-05-16)


### Bug Fixes

* pr title ([#283](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/283)) ([848e21f](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/848e21f9a9fd8879925811f9079805c7afdac79b))

## [1.2.11](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.10...v1.2.11) (2025-05-14)


### Bug Fixes

* pr title from tag ([#281](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/281)) ([eae7276](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/eae727630555a8f99f03f0904dd471035e726206))

## [1.2.10](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.9...v1.2.10) (2025-05-13)


### Bug Fixes

* pr title ([#279](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/279)) ([8465733](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/8465733f9d52452ac5d229f147b60645b46f410f))

## [1.2.9](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.8...v1.2.9) (2025-05-13)


### Bug Fixes

* added pr title ([#276](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/276)) ([efbd5a9](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/efbd5a9982434467d14c1501617de94316da17a0))
* pr title ([#278](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/278)) ([3e8f325](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/3e8f325ea823e85aefcefe57dc3064218f7c400c))

## [1.2.8](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.7...v1.2.8) (2025-05-13)


### Bug Fixes

* action version ([#274](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/274)) ([87cccbb](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/87cccbbce054b97781700d865b22c37f7619ecb4))

## [1.2.7](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.6...v1.2.7) (2025-05-13)


### Bug Fixes

* using, hopefully fixed, action script ([#272](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/272)) ([81bcf0e](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/81bcf0ec57e00285b8514c634ea1994deea650b5))

## [1.2.6](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.5...v1.2.6) (2025-05-13)


### Bug Fixes

* yet another attempt ([#270](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/270)) ([37e042e](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/37e042e7e55bacd3dc22c3a24d1608700d4e5771))

## [1.2.5](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.4...v1.2.5) (2025-05-12)


### Bug Fixes

* mastodon secret used workflow, not action ([#267](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/267)) ([7e4f7c9](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/7e4f7c9d4966bc711e2a1cb66ae7a86ea82e1158))
* secret in workflow ([#269](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/269)) ([d2bd734](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/d2bd734e858b2211ea08c3e6d149e6b2f25d0192))

## [1.2.4](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.3...v1.2.4) (2025-05-11)


### Bug Fixes

* update mastodon action ([#265](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/265)) ([23ba7ce](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/23ba7ce9073e79966102878feac617ac503d42b1))

## [1.2.3](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.2...v1.2.3) (2025-05-11)


### Bug Fixes

* using latest fix for the announcement action ([#263](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/263)) ([efd1f88](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/efd1f88e8426cfd6071819e19f18826ce215a81a))

## [1.2.2](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.1...v1.2.2) (2025-05-08)


### Bug Fixes

* checking for double nested strings in gres and gpu settings ([#251](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/251)) ([a7eac3a](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/a7eac3a0aeff74a83ab06578c0528c7473c92afa))
* Increase account charecter limit ([#260](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/260)) ([1264de3](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/1264de3123ac638132ba76ffbf5187ff500a9a9b))

## [1.2.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.2.0...v1.2.1) (2025-04-11)


### Bug Fixes

* add lost code back in ([#254](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/254)) ([6523889](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/6523889f4bec2b42a2be2b7de6381bd9e8477d76))

## [1.2.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.1.0...v1.2.0) (2025-04-04)


### Features

* added new 'qos' resource ([#241](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/241)) ([c8cdfc4](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/c8cdfc4e122c87499495ce9789cb7058dde98013))


### Bug Fixes

* account and partition settings corrected ([#249](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/249)) ([e7a248f](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/e7a248f4aeb50886535f13f5b8d4b56036951d87))
* case insensitive matching of declared slurm account  ([#244](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/244)) ([dc9a4fd](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/dc9a4fd754fee372482e66fe1e5eff6a71558eba))

## [1.1.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.0.1...v1.1.0) (2025-03-14)


### Features

* tolerant status checks ([#232](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/232)) ([cb20135](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/cb20135d5c894cf8b013509576997002c6e6d256))


### Bug Fixes

* trying syntax fix ([#235](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/235)) ([5e591ae](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/5e591aee3a9489f33c67f79c67473244263c8673))


### Documentation

* rewrite of the documentation  ([#219](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/219)) ([7d0b44c](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/7d0b44c43841111567e42e38b4c10b84f3efe88d))

## [1.0.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v1.0.0...v1.0.1) (2025-03-13)


### Bug Fixes

* skip account setting upon user request ([#224](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/224)) ([08a867a](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/08a867a8d7768fa906872c8b8cf065a1830a7491))

## [1.0.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.15.1...v1.0.0) (2025-03-12)


### ⚠ BREAKING CHANGES

* improved GPU job support ([#173](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/173))

### Features

* improved GPU job support ([#173](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/173)) ([66dcdcf](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/66dcdcfed1b2185e7ffcf8d33ef70bf09e9b2f56))


### Bug Fixes

* another dummy commit to test release-please PR CI behaviour ([#230](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/230)) ([791ed16](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/791ed16087079105ec8166e6803e64349063cb7d))
* logdir misconstruct when leading slash in wildcard ([#220](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/220)) ([61de847](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/61de84765790af6e3b1a5bbd2970aefb748f2192))

## [0.15.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.15.0...v0.15.1) (2025-02-14)


### Bug Fixes

* missing quotes for the slurm comment ([#211](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/211)) ([44f2e2b](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/44f2e2b8defdaa2adc6e9d7ab92d60935bccd010))

## [0.15.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.14.3...v0.15.0) (2025-01-23)


### Features

* disallowing blank reports ([#204](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/204)) ([6dd0105](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/6dd0105ddf0ac37cd8074b51e5b1f3329b04ae3e))


### Bug Fixes

* initializing self.slurm_logdir ([#206](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/206)) ([b00e520](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/b00e520a1c3b4707b9ee87765a44c2da23559650))

## [0.14.3](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.14.2...v0.14.3) (2025-01-22)


### Bug Fixes

* ci runner ought to start now upon merge to main ([#199](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/199)) ([363f130](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/363f130782f557c56bbbd80ec47a9f732818e6b4))

## [0.14.2](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.14.1...v0.14.2) (2025-01-20)


### Bug Fixes

* ci runner ought to start now upon merge to main ([#189](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/189)) ([90c6bf9](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/90c6bf92a050b029bf3a32f9b6b61525dfc515b8))
* path to access the posting script ([#191](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/191)) ([d7dcbbb](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/d7dcbbb4706a8f4a81570c89cdf619f1a039a4b7))
* path to posting script ([#193](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/193)) ([d0fb3cd](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/d0fb3cd8353cca6ba6e4ccc1fa64817c57908fc1))

## [0.14.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.14.0...v0.14.1) (2025-01-17)


### Bug Fixes

* mastodonbot ([#187](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/187)) ([9c2fd03](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/9c2fd036e8ef682eedc5bc96f173d79d981f9831))

## [0.14.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.13.0...v0.14.0) (2025-01-16)


### Features

* mastodonbot ([#185](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/185)) ([4051273](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/4051273cf7c80d57462579845ffc1529d1772024))

## [0.13.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.12.1...v0.13.0) (2025-01-16)


### Features

* Improved Mastodon Bot ([#183](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/183)) ([151b0fb](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/151b0fbb8e402d5817f8b67a744d4a0205ed38f6))

## [0.12.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.12.0...v0.12.1) (2025-01-15)


### Bug Fixes

* sshare testing as an alternative to sacctmgr account tests ([#178](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/178)) ([38fa919](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/38fa919ead6554c804e95424a61170e4967c9d63))

## [0.12.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.11.2...v0.12.0) (2025-01-08)


### Features

* custom log file behaviour ([#159](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/159)) ([cc3d21b](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/cc3d21b98034e06ceab2572294fc8923616dbf55))
* experimenting with automated release post to Mastodon ([#166](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/166)) ([c06325d](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/c06325d5fae1ebd0940a6edd0136533b4de37711))


### Documentation

* fix headings in further.md ([#168](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/168)) ([531ebc6](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/531ebc672fec4c579c701add9d29d178125644e6))

## [0.11.2](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.11.1...v0.11.2) (2024-11-07)


### Bug Fixes

* sbatch stderr parsing ([#161](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/161)) ([0368197](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/0368197001afad828d810edb40a02fc4515a3d8f))
* sbatch stderr parsing [#2](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/2) ([#165](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/165)) ([348e537](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/348e537c62bf5792643acaac0a75689c37774b25))

## [0.11.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.11.0...v0.11.1) (2024-10-21)


### Documentation

* requeue ([#153](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/153)) ([d91ee5f](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/d91ee5f2c757424510cb0d600e916bde66d8261f))

## [0.11.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.10.2...v0.11.0) (2024-09-27)


### Features

* added requeue option to client ([#136](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/136)) ([b0ff160](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/b0ff160533536e2d82f738ad6e9e1a268ba616cb))

## [0.10.2](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.10.1...v0.10.2) (2024-09-11)


### Bug Fixes

* added forgotten yield in case of job preemption ([#148](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/148)) ([95e5fb7](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/95e5fb7cbeb6b874a83571328537b85493e10d97))

## [0.10.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.10.0...v0.10.1) (2024-09-07)


### Bug Fixes

* logfile quoting and scancel error handling ([#140](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/140)) ([cb5d656](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/cb5d6568dfdfa3c2235bfe89a1e6ef294ab3ad8d))

## [0.10.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.9.0...v0.10.0) (2024-08-23)


### Features

* in job stability ([#137](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/137)) ([c27f5f8](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/c27f5f8b4dcf7c2d9bc34fd4870d13ff24c0dfae))


### Bug Fixes

* add --parsable to sbatch call for a more robust output parsing ([#125](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/125)) ([5e41d05](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/5e41d0577593909f8f0f255c8de29141bfd0bbe3))
* issue [#109](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/109) - preemption is no longer considered a failed status ([#132](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/132)) ([6dad273](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/6dad273b2f09ed8f10e3c26b92e2963c382e9fb8))

## [0.9.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.8.0...v0.9.0) (2024-08-06)


### Features

* multicluster ([#56](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/56)) ([c0f8fee](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/c0f8feea745a4a97f44898a68effccb2b99834df))


### Bug Fixes

* fixed string for constraints - see issue [#58](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/58) ([#64](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/64)) ([89e10ff](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/89e10ff14d5705bb522efa74ed847e6a518da672))

## [0.8.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.7.0...v0.8.0) (2024-07-12)


### Features

* cli  ([#111](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/111)) ([b56837e](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/b56837efb61e3da89a2a5d0520e6d969ebf69137)), closes [#73](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/73)

## [0.7.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.6.0...v0.7.0) (2024-06-25)


### Features

* warning if run in job ([#78](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/78)) ([257e830](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/257e830f28d7a226a0a7dad85703298677b9173c))


### Bug Fixes

* null byte account guess ([#81](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/81)) ([92d4445](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/92d44450bae805ef4b42387b9d27b295516d39da))


### Documentation

* added mini paragraph about Conda and Env Modules ([#42](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/42)) ([c821b5e](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/c821b5ea1b7a377421eee3964bf586bb82c47183))
* added paragraphs about dynamic resource allocation ([#79](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/79)) ([06a1555](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/06a1555e0a1466576f2fea59a979d8d3e0c19df4))
* storage update ([#80](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/80)) ([7e19560](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/7e19560731ca595687856ce45c8dd9e2fc5446cc))

## [0.6.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.5.2...v0.6.0) (2024-06-07)


### Features

* will reject jobs, which attempt setting job names by 'slurm_extra' ([#93](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/93)) ([df2fd3d](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/df2fd3dfbbe1e0a606da719f33391d5c9fe9d679))

## [0.5.2](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.5.1...v0.5.2) (2024-06-04)


### Bug Fixes

* [#97](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/97) preventing node confinment ([#98](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/98)) ([fa7877f](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/fa7877f8d086883ce74db75c3246b8c050720a62))

## [0.5.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.5.0...v0.5.1) (2024-05-14)


### Bug Fixes

* allowing for accounts containing whitespace ([#86](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/86)) ([6993f2d](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/6993f2d7dd7c31fd34a79317df35ff80779f8a63))
* proper line ending status message ([#87](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/87)) ([7b94aec](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/7b94aec8fdda5d2b0f8986154b6cb07d1954b7e8))

## [0.5.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.4.5...v0.5.0) (2024-05-06)


### Features

* wildcards in comment string [#85](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/85) ([#88](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/88)) ([730cac0](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/730cac09c12a7038557ee937bc58c8c9e483c8f3))

## [0.4.5](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.4.4...v0.4.5) (2024-04-17)


### Bug Fixes

* fix path typo ([#72](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/72)) ([f64fb5a](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/f64fb5adce9dc285c0b212af22d98b4289e8ce25))

## [0.4.4](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.4.3...v0.4.4) (2024-04-15)


### Miscellaneous Chores

* release 0.4.4 ([6f2b966](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/6f2b96668b4e4f84cc1e8bcb5e123c97d3abdfd0))

## [0.4.3](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.4.2...v0.4.3) (2024-04-12)


### Bug Fixes

* always create logdir before sbatch ([#67](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/67)) ([79fb961](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/79fb9612c1ddedd1eadc07741f17a940f2d989c6))

## [0.4.2](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.4.1...v0.4.2) (2024-03-11)


### Bug Fixes

* adapt to latest snakemake-interface-executor-plugins ([#49](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/49)) ([8c7f5b1](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/8c7f5b1cbf085fb45a370c705c28a6fc030c9381))

## [0.4.1](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.4.0...v0.4.1) (2024-02-29)


### Bug Fixes

* fixes issue [#40](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/40) - ntasks set explicitly ([#44](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/44)) ([f5c2c2c](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/f5c2c2c83b17442ab261619eadd9e6f71e39b772))

## [0.4.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/compare/v0.3.2...v0.4.0) (2024-02-29)


### Features

* add wildcards to output and comment ([#35](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/35)) ([190500b](https://github.com/snakemake/snakemake-executor-plugin-slurm/commit/190500b1995cb34dd3cf8354ecfda36eae64ad2b))

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
