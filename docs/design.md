
High-level design document
==========================


Data model
----------

  - Users: Django built in user model
  - Session: Django session is used to store information under the following keys:
      - `experiments_enrollments`  **WHAT SHOULD THIS CONTAIN?**
      - `experiments_goals`
      - `experiments_session_key`  **WHEN IS IT WRITTEN?**
      - `experiments_verified_human` 
  - Cookies:
      - `sessionid` used to associate with Django session stored on server side
  - Experiments:
    - Experiments and experiment alternatives are automatically created when first
      occurrence in a template or view code appears. They are stored in table `experiments_experiment`
      
      ```
      +-----------+-------------+---------------+---------------------+--------------------+-------+------------+----------+
      | name (PK) | description | alternatives" | relevant_chi2_goals | relevant_mwu_goals | state | start_date | end_date |
      ```

  - Enrolments
    - Bots are ignored    
    - Session-based users are enroled based on session id **STORED WHERE?**
    - Logged in users are enroled based on their user id using table `experiments_enrollment`
    
      ```
      +-----+-----------------+-----------+-------------+---------------+---------+
      | id  | enrollment_date | last_seen | alternative | experiment_id | user_id |
      ```

  - Goals:
    - Definitions, goals must be created in advance and described in `settings.EXPERIMENTS_GOALS`.
    - Counters are stored in Redis using the following key names:
    
      ```  
      COUNTER_CACHE_KEY = 'experiments:participants:'
      PARTICIPANT_KEY = '%s:%s:participant' % (experiment.name, alternative_name)
      COUNTER_FREQ_CACHE_KEY = 'experiments:freq:%s'
      GOAL_KEY = '%s:%s:%s:goal' % (experiment.name, alternative_name, goal_name)
      ```

Request-response cycle
----------------------
The workflow is different for logged in users and session-based auth.

### Session users

  - `experiments.utils.SessionUser`
  - **WHAT KEYS ARE USED ON SESSION?**
  - **WHEN ARE THESE STORED?**


### Logged in users

   - `experiments.utils.AuthenticatedUser`



Goal tracking
-------------

  - Check if user is enrolled 
  - Increment appropriate counter in Redis






Analytics
---------

  - Read goal counters and enrolment denominator to compute rates
  - Compute stats



