resource "aws_s3_bucket_acl" "demo" {
  bucket = "demo-bucket"
  acl    = "public-read"
}
