ARS Bot
=======

This bot exists to automate various tasks for the [ARS Wiki](https://wiki.airraidsirens.net) and [ARS Forums](https://airraidsirens.net/forums/) with an easy to use Discord interface.


Dependencies
============

* Python 3.10+
* A Discord Bot + Bot token
* MediaWiki 1.40.1+
* A MediaWiki username/password with ``bureaucrat`` and ``bot`` permissions.
* The [ConfirmAccount](https://www.mediawiki.org/wiki/Extension:ConfirmAccount) MediaWiki extension.
* phpBB 3.3
* A phpBB username/password with ``Global moderator`` permission.
* The Aluminoid 2.0 phpBB theme.

Configuration
=============

Configuration is handled via environment variables which can conveniently be set using a ``.env`` file. A template file has been provided, so copy ``.env.example`` to ``.env`` and edit accordingly. Alternatively, each key/value may also be set as an environment variable directly.

MediaWiki Configuration
=======================

The bot requires 3 environment variables to communicate with MediaWiki:

* WIKI_BASE_URL
  * The base URL for your MediaWiki install, e.g. https://wiki.airraidsirens.net. If your wiki includes ``/w/``, then include it in the variable without the trailing ``/``.

* WIKI_USERNAME
  * The username to log in with.

* WIKI_PASSWORD
  * The password to log in with.


Generating a Discord Bot Token
==============================

Visit https://discord.com/developers/applications and either select an existing application or create a new application. Once you have created your application, select ``Bot`` on the left then click ``Reset Token`` under ``Build-A-Bot``. Note that you will only be able to see your token once, so keep it somewhere safe! Once you have your token, set it in your ``.env`` file as ``DISCORD_BOT_TOKEN=mytokenhere`` or as an environment variable.

MediaWiki Account Requests Discord Channel
==========================================

The current primary function of the bot is to bridge MediaWiki account requests via the ``ConfirmAccount`` extension to Discord. This is accomplished by using a dedicated Discord channel that only serves to display each account request with an Approve and Deny button pair. Messages not created by the bot or Discord itself will be deleted, as the goal of the channel is to be empty when there is no requests. Once you have created a channel for this purpose, set the channel ID to ``DISCORD_WIKI_ACCOUNT_REQUESTS_REACTION_CHANNEL_ID`` in your ``.env`` file or as an environment variable.

MediaWiki Logging Discord Channel
=================================

This is the channel where Discord-sourced approvals and denys of MediaWiki accounts will be sent to. Set the channel ID to ``DISCORD_WIKI_LOGS_CHANNEL_ID`` in your ``.env`` file or as an environment variable.

Bot Debug Discord Channel
=========================

This is the channel where various bot debugging information such as unhandled exceptions and other failures will be sent to. Set the channel ID to ``DISCORD_BOT_DEBUG_CHANNEL`` in your ``.env`` file or as an environment variable.

Database Migrations
===================

Run the following to generate a new migration file:

```sh
make message="this is a test" migration
```

Then once you've adjusted the generated file, run the following to run the migration:

```sh
make dbupgrade
```
