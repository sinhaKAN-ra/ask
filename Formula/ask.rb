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
  url "https://files.pythonhosted.org/packages/e0/60/54966f126807e46e32627f7f7620e064e1d9c6f1d10e51536bc1b8f0b98d/aolbeam_ask-0.1.0.tar.gz"
  sha256 "29561ae48685a92d6a99727f08b0e14e32ce1a7559733dbdedd1c027e7484a96"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "config file", shell_output("#{bin}/ask --config")
  end
end
