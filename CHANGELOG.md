# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Removed
- Fetching of Fulfillment Services from the Company change/list page.

### Changed
- Only shows Shopify Actions buttons on the change page when the Shopify URL is valid.

### Fixed
- Is Shopify URL Valid is now correctly checked on every model save.

## [2.0.1] - 2018-11-01
### Fixed
- Removed unused argument and parameter causing exception with webhook handling.

## [2.0] - 2018-10-31
### Changed
- Supports the new InventoryLevels API for Shopify.

### Added
- Mirrors Files in the connected Dropbox folder.
- Allows user to import Dropbox Inventory files.
- 
