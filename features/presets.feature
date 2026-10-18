Feature: Presets management
  As a beatmaker
  I want to duplicate and edit license tiers
  So terms match my store without touching code (price is a sale input, not part of the tier)

  Scenario: Seed has 5 tiers and never duplicates
    Given the seed presets exist
    When I reseed
    Then there are still 5 presets

  Scenario: Duplicate a preset as new tier
    Given the seed presets exist
    When I duplicate "WAV Lease" as "WAV Lease Plus"
    Then the preset list contains "WAV Lease Plus"

  Scenario: Delete a custom preset
    Given the seed presets exist
    When I create then delete a temp preset
    Then it no longer exists
