package com.refinedining.domain.nutrition;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.NoSuchElementException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

@Service
@ConditionalOnProperty("rag.catalog")
public class NutritionCatalog {
    private final ObjectMapper json;
    private final JdbcTemplate db;
    private final String version;
    private final String snapshot;
    private final String sourceUrl;

    public NutritionCatalog(ObjectMapper json, JdbcTemplate db, TransactionTemplate tx,
                            @Value("${rag.catalog}") String path) throws IOException {
        this.json = json;
        this.db = db;
        JsonNode catalog = json.readTree(Path.of(path).toFile());
        this.version = catalog.required("version").textValue();
        this.snapshot = catalog.required("snapshotId").textValue();
        this.sourceUrl = catalog.required("sourceUrl").textValue();
        var rows = catalog.required("rows");
        if (!rows.isArray() || rows.isEmpty() || rows.size() != catalog.required("rowCount").intValue()) {
            throw new IllegalArgumentException("영양 원본 행 수를 확인하세요.");
        }
        db.execute("create table if not exists rag_food (catalog_id varchar(80) not null, food_code varchar(64) not null, " +
                "food_name varchar(250) not null, row_body text not null, primary key(catalog_id,food_code))");
        tx.executeWithoutResult(state -> {
            int count = db.queryForObject("select count(*) from rag_food where catalog_id=?", Integer.class, version);
            if (count == rows.size()) return;
            if (count != 0) throw new IllegalStateException("불완전한 영양 자료 버전입니다.");
            List<Object[]> batch = new ArrayList<>();
            for (JsonNode row : rows) {
                JsonNode original = row.required("original");
                batch.add(new Object[]{version, original.required("food_cd").textValue(),
                        original.required("food_nm").textValue(), row.toString()});
            }
            db.batchUpdate("insert into rag_food(catalog_id,food_code,food_name,row_body) values(?,?,?,?)", batch);
        });
    }

    public String version() { return version; }
    public String snapshot() { return snapshot; }

    public ObjectNode food(String code) {
        List<String> rows = db.queryForList("select row_body from rag_food where catalog_id=? and food_code=?",
                String.class, version, code);
        if (rows.isEmpty()) throw new NoSuchElementException("식품코드를 찾을 수 없습니다.");
        ObjectNode result = parse(rows.get(0));
        JsonNode original = result.required("original");
        result.put("foodCd", code).put("foodNm", original.path("food_nm").asText())
                .put("version", version).put("snapshotId", snapshot).put("sourceUrl", sourceUrl);
        result.required("cells").fields().forEachRemaining(entry -> {
            var cell = (ObjectNode) entry.getValue();
            Nutrient field = Nutrient.valueOf(entry.getKey());
            cell.put("label", field.label).put("unit", field.unit);
            if ("observed".equals(cell.path("status").asText())) cell.set("value", original.get(field.name()));
            else cell.putNull("value");
        });
        return result;
    }

    public record Choice(String foodCd, String foodNm) {}

    public List<Choice> searchWords(String[] terms) {
        var clauses = new ArrayList<String>();
        List<Object> args = new ArrayList<>(List.of(version));
        for (String token : terms) {
            if (token.isBlank()) continue;
            clauses.add("food_name like ? escape '!'");
            args.add("%" + token.replace("!","!!").replace("%","!%").replace("_","!_") + "%");
        }
        if (clauses.isEmpty()) return List.of();
        return db.query("select food_code,food_name from rag_food where catalog_id=? and " +
                        String.join(" and ",clauses) + " order by food_name,food_code limit 25",
                (rs,n) -> new Choice(rs.getString(1),rs.getString(2)), args.toArray());
    }

    public List<Choice> search(String name) {
        String term = name.trim();
        if (term.isEmpty() || term.length() > 250) throw new IllegalArgumentException("검색할 식품명을 입력하세요.");
        String literal = term.replace("!", "!!").replace("%", "!%").replace("_", "!_");
        return db.query("select food_code,food_name from rag_food where catalog_id=? and " +
                        "(food_code=? or food_name like ? escape '!') order by case when food_name=? then 0 else 1 end,food_name,food_code limit 25",
                (rs, n) -> new Choice(rs.getString(1), rs.getString(2)), version, term, "%" + literal + "%", term);
    }

    ObjectNode parse(String raw) {
        try { return (ObjectNode) json.readTree(raw); }
        catch (IOException e) { throw new IllegalStateException("영양 자료 JSON을 읽을 수 없습니다.", e); }
    }

    static String digest(byte[] bytes) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
        catch (NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
    }
}
