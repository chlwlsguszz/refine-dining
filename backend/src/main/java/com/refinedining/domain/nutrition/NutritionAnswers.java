package com.refinedining.domain.nutrition;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;
import org.springframework.web.util.UriComponentsBuilder;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;
import java.util.regex.Pattern;

@Service
@ConditionalOnProperty("rag.catalog")
public class NutritionAnswers {
    private static final Pattern WEIGHT = Pattern.compile("(?i)([-+]?\\d+(?:\\.\\d+)?)\\s*(밀리리터|킬로그램|그램|리터|kg|ml|g|l)(?![a-z])");
    private static final Pattern CODE = Pattern.compile("R\\d{3}-\\d{9}-\\d{4}");
    private static final Pattern UNSUPPORTED = Pattern.compile("(?i)\\d\\s*(개|컵|인분|숟갈|스푼|온스|oz|lb|근|mg|mcg|μg|밀리그램)");
    private static final Pattern YIELD = Pattern.compile("수율|조리하면|조리했을|조리한\\s*뒤|조리\\s*후\\s*(실제|총량|무게|중량)|익힌\\s*(뒤|후)\\s*총");
    private static final Pattern INTENT = Pattern.compile("비교|차이|전후|대비|차이점");
    private static final List<Nutrient> BASIC = List.of(Nutrient.enerc,Nutrient.prot,Nutrient.fatce,Nutrient.chocdf,Nutrient.sugar,Nutrient.nat);
    private final NutritionCatalog catalog;
    private final NutritionReviews reviews;
    private final ObjectMapper json;
    private final NutritionExplanation explanations;

    public NutritionAnswers(NutritionCatalog catalog, NutritionReviews reviews, ObjectMapper json, NutritionExplanation explanations) {
        this.catalog = catalog; this.reviews = reviews; this.json = json; this.explanations = explanations;
    }

    public record Question(String question, String foodCd) {}
    private record Amount(BigDecimal value, String unit) {}

    private static Amount amount(String number, String rawUnit) {
        BigDecimal n = new BigDecimal(number);
        String unit = rawUnit.toLowerCase(Locale.ROOT);
        if (unit.equals("kg") || unit.equals("킬로그램") || unit.equals("l") || unit.equals("리터")) n = n.movePointRight(3);
        if (n.signum() <= 0 || n.compareTo(new BigDecimal("1000000")) > 0) throw new IllegalArgumentException("0보다 크고 1,000,000 이하인 g 또는 mL를 입력하세요.");
        return new Amount(n, Set.of("ml","l","밀리리터","리터").contains(unit) ? "mL" : "g");
    }

    private static Amount basis(ObjectNode food) {
        var match = WEIGHT.matcher(food.path("original").path("nut_con_srtr_qua").asText().trim());
        return match.matches() ? amount(match.group(1),match.group(2)) : null;
    }

    private List<NutritionCatalog.Choice> choices(String text) {
        var code = CODE.matcher(text);
        if (code.find()) return catalog.search(code.group());
        String term = WEIGHT.matcher(text).replaceAll(" ").replaceAll("[?？!.,]", " ");
        for (Nutrient nutrient : Nutrient.values()) {
            if (nutrient.label.length() > 1) term = term.replaceAll(Pattern.quote(nutrient.label)+"(?:이|가|을|를|은|는|의)?"," ");
        }
        term = term.replaceAll("칼로리|열량|영양성분|영양소|영양|얼마(?:나|인가요|예요|나요)?|알려\\s*(?:줘|주세요)|보여\\s*(?:줘|주세요)|비교(?:해\\s*(?:줘|주세요))?|차이(?:가|는)?|같은\\s*중량|설명(?:해\\s*줘)?|이유|들어\\s*있(?:나요|어|어요|습니까)|함량|무게|조리\\s*전후", " ")
                .replaceAll("(?:에는|에서|으로|의|을|를|은|는|와|과)(?=\\s|$)", " ").trim();
        if (term.isBlank()) return List.of();
        String name = term.replaceAll("\\s+", "_");
        var matches = catalog.search(name);
        var exact = matches.stream().filter(c -> c.foodNm().equals(name)).toList();
        if (!exact.isEmpty()) return exact;
        if (!matches.isEmpty()) return matches;
        return catalog.searchWords(term.split("[_\\s]+"));
    }

    public ObjectNode answer(Question request) {
        if (request == null || request.question() == null || request.question().isBlank() || request.question().length() > 300)
            throw new IllegalArgumentException("질문은 1~300자로 입력하세요.");
        String text = request.question().trim();
        var result = json.createObjectNode();
        result.putArray("choices"); result.putArray("foods"); result.putArray("rows"); result.putNull("relation");
        if (YIELD.matcher(text).find()) return status(result,"NEED_YIELD","실제 조리 후 총량에는 조리 후 중량이나 해당 표본의 수율이 필요합니다.");
        if (UNSUPPORTED.matcher(text).find()) return status(result,"NEED_UNIT","질문에 사용할 중량(g) 또는 부피(mL)를 알려주세요.");
        String selected = request.foodCd();
        List<String> explicit = CODE.matcher(text).results().map(m -> m.group()).distinct().toList();
        if (explicit.size() > 1) {
            if (explicit.size() != 2) return status(result,"HELD","비교할 식품 두 개를 선택하세요.");
            String targetCode = null;
            for (String code : explicit) {
                if (selected != null && !selected.isBlank() && !selected.equals(code)) continue;
                var pair = reviews.approved(code);
                if (pair.isPresent() && explicit.contains(pair.get().required("selectedCd").asText())) targetCode = code;
            }
            if (targetCode == null) return status(result,"HELD","지정한 두 식품 사이에 승인된 비교 관계가 없습니다.");
            selected = targetCode;
        }
        if (selected == null || selected.isBlank()) {
            var matches = choices(text);
            if (matches.isEmpty()) return status(result,"NO_MATCH","식품명 또는 원문 식품코드를 입력하세요.");
            if (matches.size() != 1) {
                result.set("choices",json.valueToTree(matches));
                return status(result,"CHOOSE_FOOD","원문 식품을 선택하세요. 같은 이름의 다른 부위·가공 상태가 있을 수 있습니다.");
            }
            selected = matches.get(0).foodCd();
        }
        ObjectNode target = catalog.food(selected);
        cite(result.withArray("foods"),target);
        Amount base = basis(target);
        var match = WEIGHT.matcher(text);
        Amount requested = match.find() ? amount(match.group(1),match.group(2)) : base;
        if (base == null || requested == null || !base.unit.equals(requested.unit) || match.find()) {
            return status(result,"NEED_UNIT","원문의 기준 단위에 맞는 중량 또는 부피 하나를 입력하세요.");
        }
        result.put("amount",requested.value).put("unit",requested.unit);
        boolean compare = explicit.size() == 2 || INTENT.matcher(text).find();
        ObjectNode relation = compare ? reviews.approved(selected).orElse(null) : null;
        ObjectNode candidate = relation == null ? null : catalog.food(relation.required("selectedCd").asText());
        Amount candidateBasis = candidate == null ? null : basis(candidate);
        boolean comparable = candidateBasis != null && candidateBasis.unit.equals(base.unit);
        if (candidate != null) {
            cite(result.withArray("foods"),candidate);
            ObjectNode publicReview = relation.deepCopy();
            publicReview.remove(List.of("candidates","reviewer"));
            result.set("relation",publicReview);
        }
        for (Nutrient field : fields(text)) {
            JsonNode cell = target.required("cells").required(field.name());
            var line = result.withArray("rows").addObject();
            line.put("key",field.name()).put("label",field.label).put("unit",field.unit).put("status",cell.path("status").asText());
            var targetValue = scaled(cell,base,requested);
            line.put("target",display(targetValue)); line.putNull("candidate"); line.putNull("delta"); line.putNull("candidateStatus");
            if (comparable) {
                JsonNode other = candidate.required("cells").required(field.name());
                var rawValue = scaled(other,candidateBasis,requested);
                line.put("candidateStatus",other.path("status").asText()).put("candidate",display(rawValue));
                if (rawValue != null && targetValue != null) line.put("delta",display(targetValue.subtract(rawValue)));
            }
        }
        if (compare && relation == null) return status(result,"HELD",
                "승인된 생것 연결이 없어 해당 식품의 확인된 단일 영양값만 표시합니다. " + reviews.missingEvidence(selected).orElse("").trim());
        if (compare && !comparable) return status(result,"NEED_UNIT","두 원문의 기준 단위가 달라 영양 차이를 계산할 수 없습니다.");
        String message = compare ? "같은 양에서 대상 식품의 값에서 생것의 값을 뺀 차이입니다." : "선택한 식품의 원문 기준량으로 환산했습니다.";
        if (relation != null && (text.contains("설명") || text.contains("이유"))) message += " " + explanations.explain(result);
        return status(result,"ANSWER",message);
    }

    private void cite(ArrayNode foods, ObjectNode food) {
        String code = food.path("foodCd").asText();
        String href = UriComponentsBuilder.fromPath("/api/nutrition/foods/{code}").queryParam("version",catalog.version()).buildAndExpand(code).encode().toUriString();
        foods.addObject().put("foodCd",code).put("foodNm",food.path("foodNm").asText())
                .put("basis",food.path("original").path("nut_con_srtr_qua").asText()).put("href",href);
    }

    private static List<Nutrient> fields(String text) {
        List<Nutrient> chosen = Arrays.stream(Nutrient.values()).filter(f -> f.label.length() > 1 ? text.contains(f.label)
                : Pattern.compile("(?<![가-힣])"+f.label+"(?:분|은|는|이|가)?(?![가-힣])").matcher(text).find()).toList();
        if (chosen.isEmpty() && (text.contains("열량") || text.contains("칼로리"))) return List.of(Nutrient.enerc);
        return chosen.isEmpty() ? BASIC : chosen;
    }

    private static BigDecimal scaled(JsonNode cell, Amount basis, Amount portion) {
        if (!"observed".equals(cell.path("status").asText())) return null;
        return new BigDecimal(cell.required("sourceText").asText()).multiply(portion.value)
                .divide(basis.value,12,RoundingMode.HALF_UP);
    }
    private static BigDecimal display(BigDecimal n) { return n == null ? null : n.setScale(3,RoundingMode.HALF_UP).stripTrailingZeros(); }
    private static ObjectNode status(ObjectNode out, String tag, String message) { return out.put("status",tag).put("message",message); }
}
