# Changelog

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
