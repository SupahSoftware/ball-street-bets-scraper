It's time to convert this to a docker compose setup and make a bunch of other big changes.

===== CONTAINER BEHAVIOR =====

The container will run a cron every day at 10 am to fetch all of the queries we have. Maybe with a 5 seconds delay in between each query.
So cron starts, triggers first query and gets results, pause 5 seconds, next query, repeat until all queries made. 

===== MORE FILTERING =====

We need a way to filter out parallels thats squeak through. Some people don't put /50 in the title and instead will just say "Gold raywave" or "Black raywave" whatever. So we need to remove common parallels by name too. This can be tricky though, because if we remove titles with say "BLACK" in them we will filter out players with the last name "Black". Colors as last names is quite common. We also can't just rely on listing a bunch of parallel names "Raywave" etc because sometimes the parallel is literally just called "Blue" or whatever. Let me know your thoughts on this and give me a prompt. Maybe we can solve this later

===== DATABASE =====

We will need a data base to store price results in. Either sql, or postgres, etc. Let me know your thoughts and give me a prompt
We don't want to store ALL the results in the database, just the final filtered results (after we remove parallels, graded cards, etc).
DB will need columns for
-unique_id (combination of year and serial without characters. So "2025-CPAJB-mmddyyyy") (where mmddyyyy is the current mmddyyyy)
-player_name (Not sure how we should do this yet. Maybe give me a prompt with a few ideas)
-serial (Full string including characters, eg #CPA-JB)
-year (the year of the card, not the current year. Can just use the year from the query we ran)
-set (Bowman, or Topps)
-price (in pennies, eg "$3.59 will be 359)
-created_at (the date that it was written, not the date from ebay)
-card_title (full card title so we have a raw record of what we stored)

the unique id will help us prevent from writing duplicate rows, so each card can only have one entry per day

===== QUERIES FOR CRONJOB =====

Every year, we will have a few more queries to add (as new sets from Topps drop). We will not need the entire set information or all the sets in the year.
These should be manually entered in the codebase and maintained that way. But ideally they will look like this
"2025 Bowman #CPA-" and "2025 Topps Chrome #USC" I want them all stored in a list in a single file so they are easy to get to and see

===== MISC =====
-let's add a helper script so we can dump some DB records whenever we want. maybe with a --limit so we can grab the most recent X records. just output the results
to the console
-i would still like a quick entry point to run a test query like we currently have "python -m scraper search "2025 bowman #CPA-" --debug --limit 240" that only prints results like it does today and does not store anything


===== RISKS AND MISSES =====

Please analyze the plan above and look for gaps that I may have missed. ex, Is fetching a few dozen queries a day from the ebay scraper we built with 5 seconds delay
in between each too much?