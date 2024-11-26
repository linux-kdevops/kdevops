```
+---------------------------------------------+    +---------------------------
|                Mailing List Patches         |    |  Direct dev branch pushes |
|---------------------------------------------|    |---------------------------|-
| - Patches submitted to mailing lists        |    | - Developers push         |
| - Example: linux-modules vger list          |    |   branches directly       |
+----------------------+----------------------+    +-------------------+-------
               |                                             |
               |                                             |
               v                                             v
     +----------------+                 +--------------------------+
     |   Patchwork    |                 |        Topic KPD Tree    |
     |----------------|                 |--------------------------|
     | - Tracks patch |                 | - Receives branches from |
     |   submissions  |                 |   dev-tree from KPD App  |
     | - Sends series |                 |   and direct developer   |
     |   to GitHub    |                 |   pushes                 |
     +----------------+                 | - Adds `kdevops-ci` as   |
           |                            |   the first commit for   |
           |                            |   patches from Patchwork |
           v                            | - Developers merge       |
     +--------------------------+       |  `kdevops-ci` as the     |
     |     GitHub KPD Topic     |--->   |last step in their dev    |
     |          App             |       +----------+--------------+
     |--------------------------+                  |
     | - Adds `kdevops-ci` as   |                  |
     |   the first commit and   |                  |
     |   applies patch series   |                  |
     | - Pushes branch to KPD   |                  |
     |   topic tree             |                  |
     +--------------------------+                  |
                                                   |
                                                   v
                           +--------------------------+
                           |  github CI / gitlab CI   |
                           |--------------------------|
                           | - Executes CI workflows  |
                           |   on topic branches      |
                           | - Uses kdevops for       |
                           |   testing workflows      |
                           | - Uploads zip artifacts  |
                           +--------------------------+
                                      |
                                      v
                            +--------------------------+
                            |          kdevops         |
                            |--------------------------|
                            | - Orchestrates testing   |
                            |   configurations         |
                            | - Manages ansible tasks  |
                            | - pushes the results to
                            |   kdevops-results-archive|
                            +--------------------------+
                                        |
                                        v
                             +--------------------------+
                             |  kdevops-results-archive |
                             |--------------------------|
                             | - Archives results in    |
                             |   using (git LFS)        |
                             +--------------------------+
```
