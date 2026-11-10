package com.refinedining.domain.nutrition;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Instant;
import java.util.*;

@Service
@ConditionalOnProperty("rag.catalog")
public class NutritionReviews {
    private final JdbcTemplate db;
    private final NutritionCatalog catalog;
    private final String release;

    public NutritionReviews(NutritionCatalog catalog, JdbcTemplate db, ObjectMapper json, TransactionTemplate tx,
                            @Value("${rag.proposals}") String proposals) throws IOException {
        this.catalog = catalog;
        this.db = db;
        var report = json.readTree(Path.of(proposals).toFile());
        if (!catalog.snapshot().equals(report.required("snapshotId").asText())) {
            throw new IllegalArgumentException("제안과 영양 원본의 스냅샷이 다릅니다.");
        }
        var prepared = new TreeMap<String, ObjectNode>();
        for (JsonNode item : report.required("results")) {
            ObjectNode proposal = json.createObjectNode();
            for (String field : List.of("targetCd","targetQuote","selectedCd","verdict","reason","candidates","evidenceSource")) {
                proposal.set(field, item.get(field));
            }
            String code = proposal.required("targetCd").asText();
            var target = catalog.food(code);
            if (!target.path("foodNm").equals(proposal.path("targetQuote"))) throw new IllegalArgumentException("대상 원문이 다릅니다.");
            JsonNode selection = proposal.path("selectedCd");
            String verdict = proposal.required("verdict").asText();
            if (!Set.of("보류","직접 비교","참고 비교").contains(verdict) || selection.isNull() != "보류".equals(verdict)) {
                throw new IllegalArgumentException("판정과 선택 코드가 맞지 않습니다.");
            }
            Set<String> candidates = new HashSet<>();
            for (JsonNode candidate : proposal.required("candidates")) {
                JsonNode record = candidate.required("record");
                String candidateCode = record.required("foodCd").asText();
                var raw = catalog.food(candidateCode);
                if (!"01".equals(raw.path("original").path("food_lv7cd").asText()) ||
                        !raw.path("foodNm").equals(record.path("foodNm")) || !candidates.add(candidateCode)) {
                    throw new IllegalArgumentException("생것 후보 원문이 다릅니다.");
                }
            }
            if (!selection.isNull() && !candidates.contains(selection.asText())) throw new IllegalArgumentException("후보에 없는 식품입니다.");
            if (prepared.put(code, proposal) != null) throw new IllegalArgumentException("중복된 대상 식품입니다.");
        }
        // Evidence, candidate records and source version are part of the approval boundary.
        release = NutritionCatalog.digest(json.writeValueAsBytes(List.of(catalog.version(), report.required("policyVersion"), prepared)));
        db.execute("create table if not exists rag_proposal (review_id varchar(64) primary key, release_id varchar(64) not null," +
                "target_cd varchar(64) not null, body text not null, unique(release_id,target_cd))");
        db.execute("create table if not exists rag_review (review_id varchar(64) primary key, decision varchar(16) not null," +
                "reviewer varchar(120) not null, note varchar(1000) not null, decided_at varchar(40) not null)");
        tx.executeWithoutResult(state -> {
            int existing = db.queryForObject("select count(*) from rag_proposal where release_id=?", Integer.class, release);
            if (existing == prepared.size()) return;
            if (existing != 0) throw new IllegalStateException("불완전한 제안 묶음입니다.");
            List<Object[]> batch = new ArrayList<>();
            prepared.forEach((code, p) -> {
                String id = NutritionCatalog.digest((release + "/" + code).getBytes(StandardCharsets.UTF_8));
                batch.add(new Object[]{id, release, code, p.toString()});
            });
            db.batchUpdate("insert into rag_proposal(review_id,release_id,target_cd,body) values(?,?,?,?)", batch);
        });
    }

    private static final String READ = "select p.review_id,p.body,r.decision,r.reviewer,r.note,r.decided_at " +
            "from rag_proposal p left join rag_review r on p.review_id=r.review_id where p.release_id=? ";

    private List<ObjectNode> load(String condition, Object... args) {
        List<Object> params = new ArrayList<>();
        params.add(release);
        params.addAll(Arrays.asList(args));
        return db.query(READ + condition, (rs, n) -> {
            var doc = catalog.parse(rs.getString(2));
            doc.put("reviewId", rs.getString(1)).put("version", catalog.version())
                    .put("reviewStatus", Objects.toString(rs.getString(3), "PENDING"))
                    .put("reviewer", rs.getString(4)).put("note", rs.getString(5)).put("decidedAt", rs.getString(6));
            return doc;
        }, params.toArray());
    }

    public List<ObjectNode> all() { return load("order by p.target_cd"); }

    public Optional<ObjectNode> approved(String targetCd) {
        return load("and p.target_cd=? and r.decision='APPROVED'", targetCd).stream().findFirst();
    }

    public record Decision(String decision, String reviewer, String note) {}

    @Transactional
    public ObjectNode review(String id, Decision input) {
        if (input == null || !List.of("APPROVED","HELD").contains(Objects.toString(input.decision(), "")) ||
                input.note() == null || input.note().isBlank() || input.note().length() > 1000 ||
                input.reviewer() == null || input.reviewer().isBlank() || input.reviewer().length() > 120) {
            throw new IllegalArgumentException("결정·검수자·근거를 입력하세요.");
        }
        if (db.queryForList("select review_id from rag_proposal where release_id=? and review_id=? for update", String.class, release, id).isEmpty()) {
            throw new NoSuchElementException("현재 자료의 제안을 다시 여세요.");
        }
        ObjectNode p = load("and p.review_id=?", id).get(0);
        if (!"PENDING".equals(p.path("reviewStatus").asText())) {
            if (input.decision().equals(p.path("reviewStatus").asText()) && input.note().trim().equals(p.path("note").asText())
                    && input.reviewer().trim().equals(p.path("reviewer").asText())) return p;
            throw new IllegalArgumentException("이미 처리한 제안입니다.");
        }
        if ("APPROVED".equals(input.decision()) && p.path("selectedCd").isNull()) throw new IllegalArgumentException("연결할 후보가 없습니다.");
        db.update("insert into rag_review(review_id,decision,reviewer,note,decided_at) values(?,?,?,?,?)",
                id, input.decision(), input.reviewer().trim(), input.note().trim(), Instant.now().toString());
        return load("and p.review_id=?", id).get(0);
    }
}
