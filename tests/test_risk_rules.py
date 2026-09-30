from app.analyzer import find_risky, heuristic_verdict
from app.diff_parser import parse_diff


def d(path, *lines):
    return (f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n"
            + "\n".join(lines) + "\n")


DELETED_DB = '''diff --git a/infra/db.tf b/infra/db.tf
deleted file mode 100644
--- a/infra/db.tf
+++ /dev/null
@@ -1,3 +0,0 @@
-resource "aws_db_instance" "prod" {
-  engine = "postgres"
-}
'''


def names(diff):
    return [r for r, _ in find_risky(diff)]


def test_open_cidr_flagged():
    assert any("internet" in r for r in names(d("infra/sg.tf", '+  cidr_blocks = ["0.0.0.0/0"]')))


def test_wildcard_action_flagged():
    assert any("action" in r.lower() for r in names(d("infra/iam.tf", '+    actions = ["s3:*"]')))


def test_specific_action_not_flagged():
    assert names(d("infra/iam.tf", '+    actions = ["s3:GetObject"]')) == []


def test_arn_with_wildcard_suffix_not_flagged():
    assert names(d("infra/iam.tf", '+    resources = ["arn:aws:s3:::my-bucket/*"]')) == []


def test_bare_resource_star_is_medium_floor():
    assert [f for _, f in find_risky(d("infra/iam.tf", '+    resources = ["*"]'))] == [40]


def test_removed_terraform_resource_in_deleted_file():
    assert any("Terraform" in r for r in names(DELETED_DB))


def test_removed_topic_entry():
    assert names(d("config/topics.yaml", "-  - name: orders-events"))


def test_unrelated_yaml_name_removal_not_flagged():
    assert names(d("config/app.yaml", "-  - name: foo")) == []


def test_added_resource_not_flagged():
    assert names(d("infra/new.tf", '+resource "aws_s3_bucket" "b" {')) == []


def test_readme_not_flagged():
    assert names(d("README.md", "-a", "+b")) == []


def test_floor_makes_verdict_high():
    diff = d("infra/sg.tf", '+  cidr_blocks = ["0.0.0.0/0"]')
    v = heuristic_verdict(parse_diff(diff), diff)
    assert v.level.value == "high"


def test_public_acl_flagged():
    assert names(d("infra/s3.tf", '+  acl = "public-read"'))


def test_private_acl_not_flagged():
    assert names(d("infra/s3.tf", '+  acl = "private"')) == []


def test_privileged_container_flagged():
    assert names(d("k8s/agent.yaml", "+          privileged: true"))


def test_privileged_false_not_flagged():
    assert names(d("k8s/agent.yaml", "+          privileged: false")) == []


def test_backups_disabled_flagged():
    assert names(d("infra/db.tf", "+  backup_retention_period = 0"))


def test_backups_retention_7_not_flagged():
    assert names(d("infra/db.tf", "+  backup_retention_period = 7")) == []


def test_hardcoded_key_flagged():
    assert names(d("config/app.yaml", '+  api_key: "sk_live_51H8xExampleKeyDoNotUse"'))


def test_secret_from_variable_not_flagged():
    assert names(d("infra/db.tf", '+  password = "${var.db_password}"')) == []


def test_secret_in_tests_not_flagged():
    assert names(d("tests/conftest.py", '+PASSWORD = "hunter2hunter2hunter2"')) == []


from app.analyzer import is_comment_only, is_trivial


def test_comment_only_is_trivial():
    assert is_trivial(d("infra/vpc.tf", "-# creat the vpc", "+# create the vpc"))


def test_comment_plus_code_not_trivial():
    assert not is_comment_only(d("infra/vpc.tf", "+# note", '+  cidr_block = "10.0.0.0/16"'))


def test_empty_diff_not_trivial():
    assert not is_trivial("")


def test_secret_in_comment_not_trivial():
    assert not is_trivial(d("config/app.yaml", '+# api_key: "sk_live_51H8xExampleKeyDoNotUse"'))


def test_comment_only_tf_is_low():
    diff = d("infra/vpc.tf", "-# creat the vpc", "+# create the vpc")
    assert heuristic_verdict(parse_diff(diff), diff).level.value == "low"
