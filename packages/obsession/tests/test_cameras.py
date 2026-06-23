"""
Tests for Unit 5.2 cli/cameras hardening:
- IP address validation for camera_ip / obs_host;
- the systemd unit is written via `sudo tee` reading stdin (no shell-interpolated
  `echo '...' | sudo tee`), so service content can never break out into the shell.
"""

from unittest.mock import patch, MagicMock

import pytest

from obsession.cli import cameras


class TestIPValidation:
    def test_valid_ipv4_accepted(self):
        assert cameras.validate_ip("192.168.8.179") is True

    def test_invalid_ip_rejected(self):
        assert cameras.validate_ip("not-an-ip") is False
        assert cameras.validate_ip("999.1.1.1") is False
        assert cameras.validate_ip("192.168.8.179; rm -rf /") is False

    def test_deploy_rejects_invalid_camera_ip(self):
        with patch("obsession.cli.cameras.subprocess.run") as mock_run:
            result = cameras.deploy_to_camera("bogus-host")
            assert result is False
            mock_run.assert_not_called()

    def test_deploy_rejects_invalid_obs_host(self):
        with patch("obsession.cli.cameras.subprocess.run") as mock_run:
            result = cameras.deploy_to_camera("192.168.8.50", obs_host="evil;reboot")
            assert result is False
            mock_run.assert_not_called()


class TestServiceContentViaStdin:
    def test_unit_written_via_tee_stdin_not_echo(self):
        """The unit file is piped to `sudo tee` over stdin, never echo|tee."""
        completed = MagicMock(returncode=0, stderr="")
        with patch(
            "obsession.cli.cameras.subprocess.run", return_value=completed
        ) as mock_run:
            assert cameras.deploy_to_camera("192.168.8.50") is True

        # The first invocation writes the unit file.
        first_cmd = mock_run.call_args_list[0]
        argv = first_cmd[0][0]
        # No shell-interpolated echo of the service content.
        assert not any("echo" in str(tok) for tok in argv)
        assert any("tee" in str(tok) for tok in argv)
        # Service content is delivered through stdin, not the command string.
        assert "input" in first_cmd.kwargs
        assert "[Unit]" in first_cmd.kwargs["input"]


def test_main_deploy_rejects_bad_ip_exits_nonzero():
    with patch("sys.argv", ["cameras.py", "deploy", "bad-ip"]):
        with patch("obsession.cli.cameras.subprocess.run") as mock_run:
            with pytest.raises(SystemExit) as exc:
                cameras.main()
            assert exc.value.code == 1
            mock_run.assert_not_called()
