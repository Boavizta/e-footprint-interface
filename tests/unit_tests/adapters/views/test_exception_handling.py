from urllib.parse import parse_qs, urlparse

from model_builder.adapters.views.exception_handling import build_feedback_email_url, build_report_bug_url


def test_exception_urls_retain_type_without_message_or_traceback():
    secret_message = "customer-secret-value"
    error = ValueError(secret_message)

    github_url = build_report_bug_url(error)
    email_url = build_feedback_email_url("bug", error)
    github_body = parse_qs(urlparse(github_url).query)["body"][0]
    email_body = parse_qs(urlparse(email_url).query)["body"][0]

    assert "ValueError" in github_body
    assert "ValueError" in email_body
    for outbound_value in (github_url, email_url, github_body, email_body):
        assert secret_message not in outbound_value
        assert "Traceback" not in outbound_value
