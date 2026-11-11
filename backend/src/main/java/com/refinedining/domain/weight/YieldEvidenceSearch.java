package com.refinedining.domain.weight;

import org.springframework.stereotype.Service;
import java.util.*;

@Service
public class YieldEvidenceSearch {
    public record Match(MeasuredYieldCatalog.Evidence evidence, Double score, String relation,
                        List<String> reasons, List<String> differences, boolean canEstimate) {}
    public record Result(String query, String engine, int sourceCount, String message, List<Match> matches) {}
    private final MeasuredYieldCatalog catalog;
    private final YieldNameSuggestions retriever;

    public YieldEvidenceSearch(MeasuredYieldCatalog catalog, YieldNameSuggestions retriever) {
        this.catalog = catalog;
        this.retriever = retriever;
    }

    public Result search(String foodName, String cookingMethod) {
        if (foodName == null || foodName.isBlank() || foodName.length() > 250
                || (cookingMethod != null && cookingMethod.length() > 100))
            throw new IllegalArgumentException("식품명을 입력하고 검색어 길이를 확인해 주세요.");
        String name = foodName.strip();
        var conditions = new YieldQueryConditions(name, cookingMethod);
        var entries = catalog.searchEntries();
        if (conditions.outsideCorpus()) return new Result(name, "SCOPE", entries.size(),
                "현재 실측 자료는 육류·가금류입니다. 입력한 식품에 적용할 자료를 찾지 못했습니다.", List.of());
        var ranking = retriever.search(name, cookingMethod);
        String engine = ranking == null ? "NAME" : "E5";
        Map<String, Double> ranked = new LinkedHashMap<>();
        Set<String> known = new HashSet<>();
        entries.forEach(entry -> known.add(entry.source().id()));
        // Exact matches stay visible even when a vector tie pushes one below the retrieval boundary.
        catalog.candidates(name, null, cookingMethod).forEach(row -> ranked.put(row.id(), null));
        if (ranking != null) {
            for (var item : ranking.matches()) {
                if (item != null && known.contains(item.id()) && item.score() != null && Double.isFinite(item.score())
                        && item.score() >= -1 && item.score() <= 1) ranked.put(item.id(), item.score());
            }
        } else {
            entries.stream().filter(entry -> conditions.lexicalScore(entry) > 0)
                    .sorted(Comparator.<MeasuredYieldCatalog.Entry>comparingInt(conditions::lexicalScore).reversed()
                            .thenComparing(entry -> entry.source().id()))
                    .limit(12).forEach(entry -> ranked.putIfAbsent(entry.source().id(), null));
        }
        Map<String, MeasuredYieldCatalog.Entry> byId = new HashMap<>();
        entries.forEach(entry -> byId.put(entry.source().id(), entry));
        List<Match> matches = new ArrayList<>();
        ranked.entrySet().stream().limit(12).forEach(item -> {
            var entry = byId.get(item.getKey());
            var assessment = conditions.assess(entry);
            String relation = !assessment.canEstimate() ? "INCOMPATIBLE" : assessment.exact() ? "MATCH" : "REFERENCE";
            matches.add(new Match(entry.source(), item.getValue(), relation, assessment.reasons(),
                    assessment.differences(), assessment.canEstimate()));
        });
        String message = matches.isEmpty() ? "관련 실측 자료를 찾지 못했습니다. 식품·부위·조리법을 바꾸어 검색하거나 직접 잰 중량을 입력해 주세요."
                : ranking == null ? "유사 검색에 연결할 수 없어 이름과 부위가 대응하는 자료를 표시합니다."
                : "비슷한 실측 자료를 찾았습니다. 입력한 식품과의 차이 및 실험 조건을 확인해 주세요.";
        return new Result(name, engine, entries.size(), message, List.copyOf(matches));
    }
}
