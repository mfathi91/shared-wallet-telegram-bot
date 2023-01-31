# Shared wallet Telegram bot
This is a Telegram bot to do money accounting between two persons. If you lend/borrow some money to/from someone, you'd want to keep an eye on
how much each person owes the other one. This bot does this accounting for you.

## Notes:
* The bot can manage multiple wallets, e.g. Dollar, Euro, Pound, ... . This can be configured in `volumes/config.json`.
* The bot will be private to the two persons whose chat IDs is configured in `volumes/cinfig.json`.  

## Example:
Having `Julia` and `Jack` configured in `volumes/config.json`, the bot can keep the status of their balances:

![alt text](diagram.png "Diagram")

## How to run (Docker)
1. Create your bot via [Bot Father](https://t.me/BotFather).
2. Get Chat IDs of the wallet owners via [IDBot](https://t.me/myidbot).
3. Clone/download the repository.
4. Configure the bot in `volumes/config.json`.
5. Run `docker compose up -d` on the repository's root directory.
