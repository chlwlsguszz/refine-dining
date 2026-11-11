-- Use the same filtered-parent definition as the refinement report. Candidate
-- retrieval below deliberately includes all raw observations before that filter.
START TRANSACTION READ ONLY;
WITH eligible AS (
    SELECT id, src_cd, food_lv4cd, food_lv6cd, food_lv7cd
    FROM raw_food_materials
    WHERE food_nm IS NOT NULL
      AND (COALESCE(src_cd, '') <> '2'
           OR (food_nm LIKE '%대표%' AND food_nm LIKE '%평균%'))
      AND food_lv6cd REGEXP '[^[:space:]]'
),
candidate_groups AS (
    SELECT src_cd, food_lv4cd, food_lv6cd
    FROM raw_food_materials
    WHERE food_lv7cd = '01'
    GROUP BY src_cd, food_lv4cd, food_lv6cd
    HAVING COUNT(*) > 1
),
targets AS (
    SELECT e.id, e.src_cd, e.food_lv4cd, e.food_lv6cd
    FROM eligible e
    JOIN candidate_groups cg USING (src_cd, food_lv4cd, food_lv6cd)
    WHERE NOT EXISTS (
        SELECT 1 FROM eligible parent
        WHERE parent.food_lv6cd = e.food_lv6cd AND parent.food_lv7cd = '01'
    )
),
documents AS (
    SELECT id, food_cd, src_cd, food_lv4cd, food_lv6cd, food_lv7cd,
           JSON_OBJECT(
               'foodCd', food_cd, 'foodNm', food_nm,
               'srcCd', src_cd, 'srcNm', src_nm,
               'lv4Cd', food_lv4cd, 'lv4Nm', food_lv4nm,
               'lv5Cd', food_lv5cd, 'lv5Nm', food_lv5nm,
               'lv6Cd', food_lv6cd, 'lv6Nm', food_lv6nm,
               'lv7Cd', food_lv7cd, 'lv7Nm', food_lv7nm,
               'basis', nut_con_srtr_qua, 'region', food_coo_rgn_nm,
               'country', coo_nm, 'month', prd_coll_cap_mon,
               'imported', impt_yn, 'production', data_prod_nm,
               'referenceDate', crtr_ymd
           ) AS original
    FROM raw_food_materials
)
SELECT JSON_OBJECT('target', target.original, 'candidate', candidate.original)
FROM targets t
JOIN documents target ON target.id = t.id
JOIN documents candidate ON candidate.src_cd = t.src_cd
    AND candidate.food_lv4cd = t.food_lv4cd
    AND candidate.food_lv6cd = t.food_lv6cd
    AND candidate.food_lv7cd = '01'
ORDER BY BINARY target.food_cd, BINARY candidate.food_cd;
COMMIT;
