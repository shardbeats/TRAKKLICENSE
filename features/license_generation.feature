Feature: License generation
  As a beatmaker
  I want to generate a license from a preset in seconds
  So I can sell outside BeatStars without hand-editing contracts

  Scenario: Generate a non-exclusive WAV lease
    Given the seed presets exist
    When I generate a WAV lease for "Demo Beat" to "Demo Artist"
    Then the text contains the beat title and no unfilled vars
    And validation passes

  Scenario: Missing required fields are reported
    Given the seed presets exist
    When I generate with an empty customer fullname
    Then validation reports CUSTOMER_FULLNAME

  Scenario: Price words are auto-filled
    Given the seed presets exist
    When I generate a lease priced "99 USD" without price words
    Then the text contains "ninety-nine USD"

  Scenario: Exclusive template keeps 25 sections
    Given the seed presets exist
    When I generate an exclusive license
    Then the text contains "25. ACCEPTANCE" and "10-year"
    And no personal data leaks
