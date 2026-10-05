# Homebrew formula for `ask` (package: aolbeam-ask).
#
# This lives in your TAP repo (e.g. github.com/sinhaKAN-ra/homebrew-tap) at
# Formula/ask.rb, so users install with:  brew install sinhaKAN-ra/tap/ask
#
# PLACEHOLDERS to fill after the first PyPI release:
#   - url  : the exact sdist URL from https://pypi.org/project/aolbeam-ask/#files
#   - sha256: shasum -a 256 of that downloaded .tar.gz
# Get both with:  pip download aolbeam-ask --no-deps --no-binary :all:
class Ask < Formula
  include Language::Python::Virtualenv

  desc "Lightweight, stateless terminal AI CLI that knows when to search the web"
  homepage "https://ask.aolbeam.com"
  url "https://files.pythonhosted.org/packages/source/a/aolbeam-ask/aolbeam_ask-0.1.0.tar.gz" # TODO: real sdist URL
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"           # TODO: real sha256
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "config file", shell_output("#{bin}/ask --config")
  end
end
