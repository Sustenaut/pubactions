Feature: The pr-label action says whether a run's pull request carries a label
  One label a person sets on a pull request, "refresh cache" by default,
  can steer what a run does with it. The pull request is the event's own
  (pull_request, pull_request_target), the one a merge queue group is for
  (merge_group), or the ones merged into a pushed commit (push). Each
  scenario runs the action's step as GitHub does, with its inputs in the
  environment, the event in a file, and a stand-in curl that answers
  GitHub's API from files: a pushed commit "abc123" whose merged pull
  request carries "Refresh Cache", a commit "def456" whose carries "docs",
  and pull request 15, which carries "refresh cache".

  Scenario Outline: pr-label finds the label on the run's pull request, whatever its case
    When pr-label looks for "<label>" on a <event> run, <how>
    Then the step passed
    And it wrote present=<present>

    Examples:
      | label         | event             | how                                                          | present |
      | refresh cache | pull_request      | whose pull request carries "bug" and "refresh cache"         | true    |
      | refresh cache | pull_request      | whose pull request carries no label                          | false   |
      | refresh cache | pull_request      | whose pull request carries "Refresh Cache"                   | true    |
      | refresh cache | pull_request_target | whose pull request carries "refresh cache"                 | true    |
      | bug           | pull_request      | whose pull request carries "bug" and "refresh cache"         | true    |
      | refresh cache | merge_group       | for the queue branch "gh-readonly-queue/main/pr-15-0123abcd" | true    |
      | refresh cache | push              | of the commit "abc123"                                       | true    |
      | refresh cache | push              | of the commit "def456"                                       | false   |
      | refresh cache | schedule          | with no pull request                                         | false   |

  Scenario: A pushed commit whose pull requests cannot be read fails the step
    When pr-label looks for "refresh cache" on a push run, of the commit "missing"
    Then the step failed
    And it wrote nothing

  Scenario: The label is "refresh cache" by default, and the step takes its inputs from its environment alone
    When I read the pr-label action
    Then its "label" input defaults to "refresh cache"
    And its step takes its inputs from its environment alone
