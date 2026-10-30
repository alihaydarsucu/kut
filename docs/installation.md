# Installation and configuration

## Requirements

- GRUB 2 and your distribution's configuration tool (<code>update-grub</code> or
  <code>grub-mkconfig</code>)
- Administrator privileges for installation
- A graphical GRUB mode on EFI systems

## Install

~~~bash
sudo ./install.sh
~~~

The installer:

1. Creates a backup of <code>/etc/default/grub</code>, the existing Kut theme
   directory, and Kut GRUB hooks under
   <code>/var/backups/kut-grub/&lt;timestamp&gt;</code>.
2. Installs the theme in <code>/boot/grub/themes/kut</code>.
3. Renders distribution, kernel, RAM, firmware, host, and CPU values into the
   theme labels.
4. Updates <code>GRUB_THEME</code>, <code>GRUB_GFXMODE</code>, and Kut settings.
5. Rebuilds <code>grub.cfg</code> with <code>update-grub</code> or, when
   appropriate, <code>grub-mkconfig</code>.

## Settings

You can change these Kut settings in <code>/etc/default/grub</code>:

| Setting | Default | Description |
| --- | --- | --- |
| <code>KUT_TELEMETRY</code> | <code>1</code> | Enables or disables the pre-menu telemetry screen. |
| <code>KUT_TELEMETRY_DELAY</code> | <code>3</code> | Telemetry duration in seconds; the accepted range is <code>1</code>–<code>10</code>. |

After changing settings, rebuild the configuration:

~~~bash
sudo update-grub
~~~

## Chroot or installation-environment test

To skip the <code>update-grub</code> call:

~~~bash
sudo KUT_SKIP_UPDATE=1 ./install.sh
~~~

This installs the files and renders labels, but does not rebuild the GRUB
configuration. Run <code>sudo update-grub</code> from the target system before
booting it.

## Uninstall

~~~bash
sudo ./uninstall.sh
~~~

The uninstaller removes only Kut's <code>GRUB_THEME</code>, telemetry settings,
theme directory, and GRUB hooks. It first creates a backup under
<code>/var/backups/kut-grub/&lt;timestamp&gt;</code> and preserves
<code>GRUB_GFXMODE</code> and <code>GRUB_TIMEOUT_STYLE</code>.
