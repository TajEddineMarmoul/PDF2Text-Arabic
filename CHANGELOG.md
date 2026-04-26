# Changelog

## [0.4.0](https://github.com/TajEddineMarmoul/PDF2Text-Arabic/compare/v0.3.0...v0.4.0) (2026-04-26)


### Features

* add security layer to discard container tables during extraction ([244fcf8](https://github.com/TajEddineMarmoul/PDF2Text-Arabic/commit/244fcf8dcbcf49048f044a8a62583828c7a1bb83))
* add single page extraction and debug image saving functionality ([bccba9e](https://github.com/TajEddineMarmoul/PDF2Text-Arabic/commit/bccba9efbcea19b44ad18f9ba6f0c66328a17ab6))
* final audited version with robust footnote linkage and character cleaning ([5c5b430](https://github.com/TajEddineMarmoul/PDF2Text-Arabic/commit/5c5b430238c36729f33ced79bd8f1df59af33975))


### Bug Fixes

* global ligature corrector for perfect Arabic text extraction ([e41b185](https://github.com/TajEddineMarmoul/PDF2Text-Arabic/commit/e41b18537db027ea78dc7c6bde86dd54227e1f0a))
* robust regex-based ligature corrector for Arabic text integrity ([3b95c27](https://github.com/TajEddineMarmoul/PDF2Text-Arabic/commit/3b95c274fbd79fd93043fec453f8a36a355cc26c))

## [0.3.0](https://github.com/crazytajdine/PDF2Text-Arabic/compare/v0.2.0...v0.3.0) (2026-04-25)


### Features

* add debugging script for extracting tables from page 18 of the financial law PDF ([3583dda](https://github.com/crazytajdine/PDF2Text-Arabic/commit/3583ddae185c80d2c6ce8a14c8a28e26ed0ef284))
* add script to extract tables from page 58 of the financial law PDF ([58bd66c](https://github.com/crazytajdine/PDF2Text-Arabic/commit/58bd66c9f94871ce3364e9acf6fddba0801a7841))
* added debug for small number ([7c111bc](https://github.com/crazytajdine/PDF2Text-Arabic/commit/7c111bccb521f7890d72b25379f86ba80ce87e2e))
* enhance table extraction and OCR region handling for improved accuracy ([1e58eb3](https://github.com/crazytajdine/PDF2Text-Arabic/commit/1e58eb31fdf95be9d392c15f23dac33ec50d28e5))
* enhance table extraction fallback logic and add debugging scripts for strategy comparison ([cbd1793](https://github.com/crazytajdine/PDF2Text-Arabic/commit/cbd17936f972d80f4b9393009ba991b51d437c1f))
* fix table selection ([bee6ea2](https://github.com/crazytajdine/PDF2Text-Arabic/commit/bee6ea2feeaa31d582a35f62ccd6339c47cd0eab))
* fixed table to be more accurate ([042cc9c](https://github.com/crazytajdine/PDF2Text-Arabic/commit/042cc9c160579860c6bed63011574f8cef4cdbd7))
* implement container discard security layer for table extraction ([79d8b9c](https://github.com/crazytajdine/PDF2Text-Arabic/commit/79d8b9cab3c302cbbb5f52beb934e854db1fb0a5))
* implement topmost linked reference strategy for robust footnote detection ([65eb6c6](https://github.com/crazytajdine/PDF2Text-Arabic/commit/65eb6c6c661d7e8db86937cc22feeb4738a9ee24))
* simplify RAG table formatting to plain CSV style without tags for better LLM context ([becfba3](https://github.com/crazytajdine/PDF2Text-Arabic/commit/becfba3f696fc3c0ae49a8f72c0f2ea1c5ceff19))
* sync between debug and extract ([2173b52](https://github.com/crazytajdine/PDF2Text-Arabic/commit/2173b52d4dd0ce9cfe61ba5c4e549eaf7f774c23))
* update table extraction format and add debugging script for specific pages ([db1ad12](https://github.com/crazytajdine/PDF2Text-Arabic/commit/db1ad12b84a99ff64bd57aff39c3c0e7ee1cfe9f))
* use full-page OCR if any unreadable image regions are detected ([c9bbfc9](https://github.com/crazytajdine/PDF2Text-Arabic/commit/c9bbfc9dc70b65c5e48f380a5ef0dad92481ad9d))


### Bug Fixes

* bug related to footer ([d97ccde](https://github.com/crazytajdine/PDF2Text-Arabic/commit/d97ccde66c96eb64644fd665a24a6bdd6d2550ef))
* ensure topless and bottomless tables are detected and extracted ([c01b168](https://github.com/crazytajdine/PDF2Text-Arabic/commit/c01b1684f67701f31bc301e7a75470d80ae01102))
* ignore tiny symbols and footnote markers in image OCR extraction ([fb856b1](https://github.com/crazytajdine/PDF2Text-Arabic/commit/fb856b173cba040f6ce21c7f16cccd968818d40a))
* test new approach for footers ([ffb0379](https://github.com/crazytajdine/PDF2Text-Arabic/commit/ffb03798c4c85eaac81f17787fa872f3728c0afa))


### Documentation

* add image assets for README ([5df661f](https://github.com/crazytajdine/PDF2Text-Arabic/commit/5df661f9bb4585c45b466989d05c219a6f4c4182))
* add visual examples of edge-case table extraction to README ([c354c88](https://github.com/crazytajdine/PDF2Text-Arabic/commit/c354c887769c55439fd52d49fc636871885656a8))
* update README with new CSV table format and advanced edge-case handling ([0253257](https://github.com/crazytajdine/PDF2Text-Arabic/commit/0253257d54887ce37853d384fcdeb4e5682637b5))

## [0.2.0](https://github.com/crazytajdine/PDF2Text-Arabic/compare/v0.1.6...v0.2.0) (2026-04-19)


### Features

* add Arabic PDF text extraction functionality with PyMuPDF ([9a85fb9](https://github.com/crazytajdine/PDF2Text-Arabic/commit/9a85fb9e63a497fa499f01daca811e957f92f91a))
* add debug visualization for extraction pipeline with overlays ([ae56bfa](https://github.com/crazytajdine/PDF2Text-Arabic/commit/ae56bfac07cba7765feb245251706dd1fdfeeec0))
* add functions to check image hashes and detect top images in PDF pages ([703f136](https://github.com/crazytajdine/PDF2Text-Arabic/commit/703f13647a5c282310ae9524f02308e19554de10))
* add release automation configuration and update settings ([cc4a1b4](https://github.com/crazytajdine/PDF2Text-Arabic/commit/cc4a1b4d6cc2472675344d2004f934a8029198bd))
* add structured extraction result and capabilities API for AI integration ([b25a568](https://github.com/crazytajdine/PDF2Text-Arabic/commit/b25a568f6fce5b6e7551c2a909c6ab42e1099347))
* add support for Gemini OCR backend and enhance error handling ([9ad3f32](https://github.com/crazytajdine/PDF2Text-Arabic/commit/9ad3f32a5376fd8e95763cc39b30f66184de8b04))
* add table extraction strategy and enhance OCR handling for mixed pages ([050382a](https://github.com/crazytajdine/PDF2Text-Arabic/commit/050382acfa75ec49147a39d7020b4eded9b534ab))
* enhance page number detection logic and update cropping parameters in CLI ([8b99539](https://github.com/crazytajdine/PDF2Text-Arabic/commit/8b995390c3a6a082af0dd0002a6a4a9126605022))
* enhance PDF extraction with column detection and aspect ratio checks ([652f99d](https://github.com/crazytajdine/PDF2Text-Arabic/commit/652f99de7afa4f1f91c8b4ae2c41695794abfc7d))
* enhance superscript detection using body font size ratio and improve footer detection logic ([63571c8](https://github.com/crazytajdine/PDF2Text-Arabic/commit/63571c838dc35970590460f2259f0a932c853032))
* implement automatic page number detection for cropping and enhance debug visualization ([ace7bc7](https://github.com/crazytajdine/PDF2Text-Arabic/commit/ace7bc7d8d615a070b4638b148b0daec6db88f38))
* implement mixed-page detection and OCR for image-based content in PDF extraction ([e355a8b](https://github.com/crazytajdine/PDF2Text-Arabic/commit/e355a8b18444b0b2cbe416db9f6047e5a19b0287))
* implement RTL reading order logic for improved text extraction ([27be40f](https://github.com/crazytajdine/PDF2Text-Arabic/commit/27be40fcf5d0a4aaf5076fa8f53c8dae473dfa2f))
* update OCR logging to use safe page number and bump version to 0.1.3 ([96db34a](https://github.com/crazytajdine/PDF2Text-Arabic/commit/96db34afd6461547eab09ae98c38f0b49cb588a8))


### Bug Fixes

* update execution counts and refine OCR output in local model test ([524acd9](https://github.com/crazytajdine/PDF2Text-Arabic/commit/524acd96ca0f5e3aa455c7fe9df3b01906d13e3f))
* update extraction logic to ignore repeating headers and standalone page numbers ([23c3378](https://github.com/crazytajdine/PDF2Text-Arabic/commit/23c3378efa5ff00bce066867765bde01c3e60dcb))
* update google-genai version to 1.73.1 and clean up settings ([e4587f9](https://github.com/crazytajdine/PDF2Text-Arabic/commit/e4587f9a8145b70c5d4c32555c54a5a71269a318))
* update settings and improve table extraction logic to filter out false positives ([b09e6ae](https://github.com/crazytajdine/PDF2Text-Arabic/commit/b09e6ae92e7f88eee5230ab5bbc037b2f575c9f9))
