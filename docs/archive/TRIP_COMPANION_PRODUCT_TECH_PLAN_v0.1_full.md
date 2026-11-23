**TRIP COMPANION**

Product Requirements, Technical Architecture & Modular Build Plan

*Version 0.1 --- Documentation baseline before implementation*

  -----------------------------------------------------------------------
  **Goal ---** Chốt một source of truth đủ rõ để nhiều model/session có
  thể build từng module độc lập mà không cần giữ toàn bộ project trong
  context.
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------

  -----------------------------------------------------------------------
  **Thuộc tính**                      **Giá trị**
  ----------------------------------- -----------------------------------
  Document owner                      Mia / project owner

  Status                              Draft for review; implementation
                                      not started from this document

  Primary stack                       Next.js + TypeScript; FastAPI +
                                      Python; PostgreSQL/PostGIS

  Core principle                      Provider adapters + domain
                                      contracts + structured AI outputs

  Build rule                          Không merge feature nếu chưa có
                                      acceptance criteria và tests tương
                                      ứng
  -----------------------------------------------------------------------

# Mục lục

1\. Executive summary

2\. Product vision & principles

3\. Users, jobs-to-be-done & reference scenario

4\. Scope: MVP, later phases, non-goals

5\. End-to-end experience: Before / During / After

6\. Functional requirements by module

7\. Recommendation systems: food, knowledge, photo spots

8\. Data sources & provider strategy

9\. Safety, privacy & responsible recommendation rules

10\. Technical architecture

11\. Domain model & database schema

12\. API contracts

13\. AI orchestration & partial regeneration

14\. Budget, split expenses & settlement logic

15\. Reliability, caching, observability & cost control

16\. Testing strategy

17\. Deployment & environments

18\. Modular repository & context-management rules

19\. Roadmap, milestones & acceptance gates

20\. Issue breakdown for modular implementation

21\. Risks & mitigations

22\. Open decisions

23\. Definition of Done

24\. References

# 1. Executive summary

Trip Companion là một travel workspace có AI, không chỉ là một itinerary
generator. Product nhận ngày đi, điểm xuất phát, điểm đến hoặc
preference mở; tìm lựa chọn transport; tạo itinerary có thể chỉnh; rồi
enrich từng stop bằng kiến thức nên đọc, food recommendation, photo
spots, practical notes và budget/settlement.

Điểm khác biệt chính là hệ thống giữ trạng thái của chuyến đi như một
evolving plan. Khi user thay đổi một phần --- ví dụ bỏ Aswan và ở lại
Luxor --- engine chỉ regenerate block bị ảnh hưởng thay vì sinh lại toàn
bộ itinerary.

Tài liệu này là baseline trước build. Mọi module sau này phải bám theo
contracts, data ownership, acceptance criteria và privacy rules trong
tài liệu. Nếu implementation cần thay đổi assumption, thay đổi phải được
ghi vào decision log trước khi code tiếp.

  -----------------------------------------------------------------------
  **Product thesis ---** Giá trị lớn nhất không nằm ở "AI tạo lịch
  trình", mà ở việc AI hiểu trip context theo thời gian và đưa đúng
  recommendation/knowledge ở đúng thời điểm: trước chuyến đi, tại điểm
  đến, và sau chuyến đi.
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------

# 2. Product vision & principles

## 2.1 Vision

Một personal travel companion có thể đưa user từ "mình muốn đi đâu đó"
đến "mình hiểu nơi mình đang đứng, ăn món phù hợp khẩu vị, chụp được góc
đẹp, quản lý được chi phí và nhớ lại chuyến đi sau khi về".

## 2.2 Product principles

  -----------------------------------------------------------------------
  **Nguyên tắc**                      **Ý nghĩa**
  ----------------------------------- -----------------------------------
  Plan from constraints, not vibes    Arrival/departure time, opening
                                      hours, travel time, energy level,
                                      luggage, bookings và must-do phải
                                      giới hạn itinerary trước khi model
                                      viết prose.

  LLM is planner, not database        Facts về flights, places, opening
                                      hours, routes và prices phải đến từ
                                      provider/retrieval layer; model
                                      dùng để rank, compose, explain và
                                      regenerate.

  Partial regeneration by default     Thay một ngày hoặc một stop không
                                      được phá các booking và ngày đã
                                      locked.

  Explain why                         User phải thấy vì sao một
                                      ngày/restaurant/route được
                                      recommend.

  Multi-currency native               Expenses giữ original currency;
                                      conversion là derived value;
                                      settlement tách khỏi trip cost.

  Preference \> demographic proxy     Food matching dựa trên taste
                                      profile và review content; không
                                      suy đoán race/ethnicity từ tên/ảnh.

  Modular by contract                 Provider, domain, orchestration và
                                      UI giao tiếp bằng typed contracts;
                                      module có thể build/test độc lập.

  Trust through provenance            Recommendation cần biết đâu là live
                                      provider data, đâu là user input,
                                      đâu là AI inference.
  -----------------------------------------------------------------------

# 3. Users, jobs-to-be-done & reference scenario

## 3.1 Primary user

-   Independent traveller hoặc nhóm nhỏ tự plan, muốn tối ưu thời gian
    nhưng không muốn dành nhiều giờ ghép flight, Maps, blogs, bookings
    và spreadsheet.

-   Có preference rõ: budget, food, history, photography, pace, comfort,
    must-do.

-   Có khả năng thay đổi plan trong chuyến đi và cần app hiểu constraint
    mới.

## 3.2 Jobs-to-be-done

-   "Khi mình có ngày nghỉ và budget, giúp mình tìm destination/flight
    hợp lý."

-   "Khi mình đã chọn destination, giúp mình tạo lịch trình khả thi theo
    giờ bay và bookings."

-   "Khi đứng ở một địa điểm, giải thích ngắn gọn mình đang nhìn gì và
    nên chú ý gì."

-   "Khi cần ăn, gợi ý nơi phù hợp khẩu vị và vị trí tiếp theo, không
    chỉ top-rated."

-   "Khi plan thay đổi, sửa đúng block liên quan mà không reset cả
    chuyến."

-   "Khi đi chung, theo dõi ai trả, ai chịu phần nào, reimbursements và
    final settlement."

## 3.3 Reference scenario: Egypt

Reference scenario dùng để kiểm tra design: user bay đến Cairo muộn, ngủ
tối đầu; tham quan Cairo/Giza; overnight desert; đi tiếp Luxor; có
balloon phụ thuộc thời tiết; sau đó bỏ Aswan và đổi ngày cuối thành
Luxor downtown. System phải giữ booking hotel/flight, thay đúng ngày
cuối, update budget/prep và không tạo conflict.

  -----------------------------------------------------------------------
  **Acceptance reference ---** Nếu engine không xử lý tốt scenario này mà
  phải regenerate toàn bộ trip hoặc làm mất booking constraints,
  architecture chưa đạt.
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------

# 4. Scope: MVP, later phases, non-goals

  -----------------------------------------------------------------------
  **MVP v1**              **Later**               **Không làm ở v1**
  ----------------------- ----------------------- -----------------------
  Create trip +           Destination inspiration Direct airline
  preferences             from flexible dates     ticketing/refunds

  Live/partner flight     Hotel search/booking    Social network/feed
  search + outbound       integrations            
  booking link                                    

  Place discovery +       Collaborative real-time Automated
  itinerary generation    editing                 immigration/visa legal
                                                  advice

  Editable itinerary +    Offline packs and       Scraping protected
  locked items            richer on-device mode   sites at scale

  Knowledge / food /      Community-generated     Race/ethnicity
  photo / practical cards photo spots             inference from
                                                  reviewers

  Budget, split,          Receipt OCR + bank      Full accounting package
  reimbursements,         connectors              
  settlement                                      

  Partial regeneration    Personalized long-term  Microservices
                          taste learning          
  -----------------------------------------------------------------------

# 5. End-to-end experience: Before / During / After

## 5.1 Before

1.  Create Trip

2.  Search / select flight

3.  Set accommodation or area

4.  Generate itinerary candidates

5.  Review travel time & opening-hours conflicts

6.  Lock bookings / must-do items

7.  Create prep checklist

8.  Generate Learn-before-you-go pack

9.  Seed budget

## 5.2 During

Home screen chuyển sang "Today". Mỗi stop hiển thị time, route, booking
state và 5 contextual actions: Know, Navigate, Eat, Photo, Practical.

TODAY --- Luxor\
07:00 Breakfast\
09:00 Luxor Museum \[Know\] \[Photo\] \[Eat nearby\]\
12:30 Downtown lunch \[Taste match 89%\]\
15:00 Corniche / café\
20:30 Collect bags\
22:30 Airport

## 5.3 After

-   Reconcile actual expenses

-   Places visited vs skipped

-   Trip journal / highlights

-   Learning recap

-   Saved restaurants/photo spots

-   Reusable preference updates

# 6. Functional requirements by module

  -----------------------------------------------------------------------------
  **Module**                          **Requirement**
  ----------------------------------- -----------------------------------------
  Trip Core                           Create/edit trip dates, travellers,
                                      origin, destinations, budget, pace,
                                      interests, hard constraints; version
                                      every major plan change.

  Flight Search                       Normalize provider flight results;
                                      filters for
                                      price/time/stops/baggage/self-transfer;
                                      selected flight becomes hard time
                                      constraint.

  Places                              Search POIs, restaurants, museums,
                                      landmarks; normalize IDs, location,
                                      categories, hours, rating, photos/reviews
                                      metadata.

  Routing                             Compute travel durations between
                                      candidate stops; use route matrix for
                                      clustering and infeasibility checks.

  Itinerary                           Generate days from constraints; support
                                      locked items, candidate scores, day
                                      capacity, travel-time penalties, partial
                                      regeneration.

  Knowledge                           Create before/during/after knowledge
                                      cards grounded in selected places; save
                                      reading state.

  Food                                Build user taste profile; extract
                                      review/dish signals; rank restaurant
                                      candidates by contextual fit.

  Photo spots                         Store place-level and sub-place photo
                                      tips: coordinates/description, best time,
                                      direction, lens/pose hints, provenance.

  Budget                              Original currency, payer, split rule,
                                      derived currencies, transfers,
                                      reimbursements, final settlement.

  During-trip                         Contextual Today view, late/skip/replan
                                      actions, nearby fallback suggestions.

  Post-trip                           Actual spend, visited places, saved
                                      knowledge and preferences, trip summary.
  -----------------------------------------------------------------------------

# 7. Recommendation systems: food, knowledge, photo spots

## 7.1 Food taste engine

Food recommendation không được classify reviewer theo race/ethnicity từ
tên, ảnh, profile hoặc suy đoán. Product tạo TasteProfile từ
user-declared preferences và feedback; review text chỉ được dùng để
extract content signals.

  -----------------------------------------------------------------------
  **Signal group**                    **Ví dụ**
  ----------------------------------- -----------------------------------
  Taste                               spicy, savory, sour, sweet, bitter,
                                      rich, smoky

  Texture                             crispy, chewy, creamy, broth-heavy

  Cuisine familiarity                 reviewer tự nói "I eat Sichuan food
                                      regularly" hoặc so sánh với cuisine
                                      họ quen

  Authenticity signals                local-style, tourist-adjusted,
                                      traditional preparation

  Context                             distance to next stop, open now,
                                      price, reservation need, dietary
                                      compatibility

  Confidence                          review volume, recency, consistency
                                      across sources
  -----------------------------------------------------------------------

taste_match = w1 \* preference_similarity\
+ w2 \* cuisine_fit\
+ w3 \* context_fit\
+ w4 \* quality_confidence\
- w5 \* travel_penalty

UI nên nói "Match for your taste: 88%" thay vì "Asian-palate score".
Language of review có thể là một filter hiển thị minh bạch, nhưng không
được biến thành identity của reviewer.

## 7.2 Knowledge cards

  -----------------------------------------------------------------------
  **Moment**                          **Card type**
  ----------------------------------- -----------------------------------
  Before                              Context primer, timeline, key
                                      concepts, names to know

  At place                            What to look for, 3--5 minute
                                      explanation, practical cue

  After                               Compare places visited, memory
                                      recap, deeper reading
  -----------------------------------------------------------------------

## 7.3 Photo spots

Photo spot không chỉ là Place Photo. Data model phải hỗ trợ
sub-location: label, approximate coordinate or relative description,
best time/light, shot direction, crowd note, lens/phone suggestion,
accessibility, provenance và confidence.

  -----------------------------------------------------------------------
  **Moat opportunity ---** Curated + user-validated photo-spot data có
  thể trở thành proprietary dataset; không nên phụ thuộc hoàn toàn vào
  generic place photos.
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------

# 8. Data sources & provider strategy

Provider layer phải normalize external data thành internal contracts.
Domain code không được gọi trực tiếp SDK/provider-specific payload.

  -------------------------------------------------------------------------------
  **Capability**          **Candidate provider /  **Design note**
                          source**                
  ----------------------- ----------------------- -------------------------------
  Flights                 Skyscanner Flights Live Search adapter; never persist
                          Prices; Duffel          stale offer as guaranteed fare.

  Places                  Google Places API (New) Search/details/photos/reviews
                                                  metadata; respect attribution
                                                  and EEA terms.

  Routing                 Google Routes API       Compute routes / route matrix;
                                                  isolate terms-sensitive map
                                                  presentation.

  Weather                 Provider adapter (TBD)  Only needed when
                                                  itinerary/weather-sensitive
                                                  activity requires it.

  Knowledge               Curated sources + web   Store source references and
                          retrieval + LLM         generated_at timestamp.

  User-generated          First-party ratings,    Own data becomes strongest
                          taste feedback, photo   personalization layer over
                          spot feedback           time.
  -------------------------------------------------------------------------------

Current provider assumptions were checked against official documentation
on 23 Nov 2026: Skyscanner documents a create/poll workflow for live
flight search; Google Places (New) exposes Text/Nearby Search, Place
Details and Photos; Routes provides Compute Routes and Compute Route
Matrix; Duffel offers can expire and should be refreshed before booking.

# 9. Safety, privacy & responsible recommendation rules

-   Không infer race, ethnicity, religion, health condition, sexual
    orientation hoặc other sensitive traits từ reviewer/user content để
    rank restaurants.

-   Không dùng nationality/race proxy khi taste profile có thể biểu diễn
    preference trực tiếp.

-   User-declared dietary restrictions được xử lý như hard constraints;
    nếu allergy có high stakes, UI phải cảnh báo verify trực tiếp với
    venue.

-   Visa/immigration information phải hiển thị source + freshness; không
    tự đảm bảo eligibility.

-   Prices, opening hours, transport availability phải mang timestamp và
    có refresh path.

-   Không lưu raw review/profile data lâu hơn cần thiết; store extracted
    non-sensitive signals khi được phép.

-   User phải có quyền xóa trip, preferences và first-party
    contributions.

# 10. Technical architecture

Browser / Mobile Web\
│\
▼\
Next.js Web App\
│ typed REST/JSON\
▼\
FastAPI Application API\
│\
├── Domain services\
│ ├── trips\
│ ├── itinerary\
│ ├── recommendations\
│ ├── knowledge\
│ └── expenses\
│\
├── Orchestration / AI\
│ ├── planner\
│ ├── partial-regenerator\
│ └── explainer\
│\
├── Provider adapters\
│ ├── flights\
│ ├── places\
│ ├── routes\
│ └── weather\
│\
▼\
PostgreSQL + PostGIS (+ vector extension if needed)\
│\
├── Redis/cache optional\
└── object storage optional

Start as a modular monolith. Microservices chỉ xem xét khi module
ownership, scale hoặc deployment cadence thực sự buộc phải tách.

## 10.1 Layer rules

  -----------------------------------------------------------------------
  **Layer**               **Được phép**           **Không được phép**
  ----------------------- ----------------------- -----------------------
  UI                      Render state, collect   Provider credentials;
                          inputs, optimistic      business rules
                          interactions            

  API/controller          Auth, validation,       Complex recommendation
                          request composition     logic

  Domain                  Deterministic business  Direct network calls
                          rules                   

  Orchestration           Call                    Own canonical data
                          domain/provider/LLM in  schema
                          workflow                

  Provider adapter        External API            Leak provider payload
                          translation             into UI/domain

  Persistence             Repositories,           Recommendation prose
                          transactions,           
                          migrations              
  -----------------------------------------------------------------------

# 11. Domain model & database schema

  -----------------------------------------------------------------------
  **Entity**                          **Purpose**
  ----------------------------------- -----------------------------------
  users                               account/profile settings; no
                                      inferred sensitive traits

  taste_profiles                      declared taste + learned feedback

  trips                               dates, origin, status, base
                                      currency

  trip_members                        member, currency preference, role

  trip_constraints                    hard/soft constraints, source, lock
                                      state

  transport_options                   normalized search result snapshot

  bookings                            confirmed external booking
                                      reference

  places                              canonical normalized place

  trip_places                         saved/candidate/visited state

  itinerary_days                      date, location, plan version

  itinerary_items                     time window, place, booking, lock
                                      state

  knowledge_cards                     before/during/after content +
                                      sources

  photo_spots                         sub-place shot data + provenance

  restaurant_signals                  extracted non-sensitive signals

  expenses                            original amount/currency, payer,
                                      category

  expense_splits                      member share rule/value

  transfers                           member-to-member cash movement

  plan_versions                       immutable snapshots / diffs

  provider_snapshots                  short-lived raw/normalized fetch
                                      metadata
  -----------------------------------------------------------------------

## 11.1 Expense invariants

-   Expense original_amount + original_currency là canonical input.

-   Converted values là derived, timestamped FX; không overwrite
    original.

-   Payer != beneficiary/share owner.

-   Transfer/reimbursement không phải trip cost; nó chỉ ảnh hưởng
    settlement.

-   Settlement phải có thể recompute từ expenses + splits + transfers.

# 12. API contracts

Endpoints dưới đây là contract-level; implementation có thể đổi path
nhưng semantics không được đổi nếu chưa update document.

POST /v1/trips\
GET /v1/trips/{trip_id}\
PATCH /v1/trips/{trip_id}\
\
POST /v1/flights/search\
POST /v1/trips/{trip_id}/transport/select\
\
POST /v1/places/search\
GET /v1/places/{place_id}\
\
POST /v1/trips/{trip_id}/itinerary/generate\
POST /v1/trips/{trip_id}/itinerary/regenerate\
PATCH /v1/itinerary/items/{item_id}\
POST /v1/itinerary/items/{item_id}/lock\
\
GET /v1/places/{place_id}/knowledge\
GET /v1/places/{place_id}/food\
GET /v1/places/{place_id}/photo-spots\
\
POST /v1/trips/{trip_id}/expenses\
POST /v1/trips/{trip_id}/transfers\
GET /v1/trips/{trip_id}/settlement

## 12.1 Example regenerate request

{\
\"scope\": {\"date\": \"2026-11-06\"},\
\"change\": \"Remove Aswan; stay around Luxor downtown\",\
\"preserve\": \[\"confirmed_bookings\", \"locked_items\",
\"flight_departure\"\],\
\"preferences\": {\"pace\": \"relaxed\"}\
}

# 13. AI orchestration & partial regeneration

AI outputs phải structured theo schema. Model không tự gọi provider
payload tùy ý và không được trả itinerary hoàn chỉnh nếu validator phát
hiện conflict.

1\. Resolve trip state\
2. Fetch/refresh required provider data\
3. Build candidate set\
4. Deterministic filtering: closed, impossible travel, hard constraints\
5. Score candidates\
6. LLM composes structured plan\
7. Validator checks conflicts\
8. Persist new plan_version\
9. Generate short "why this plan" explanation

## 13.1 Partial regeneration algorithm

1\. Identify affected date/range and dependency graph.

2\. Freeze confirmed bookings + locked itinerary items outside affected
scope.

3\. Remove only unlocked affected items.

4\. Recompute candidate places/routes inside available time window.

5\. Generate replacement plan.

6\. Validate against flight/hotel/transport constraints.

7\. Write diff and preserve old version for rollback.

# 14. Budget, split expenses & settlement logic

Budget module phải hỗ trợ giống case Egypt: USD/EUR/GBP/EGP, người front
tiền khác người chịu cost, reimbursements hai chiều, và final settlement
không double count.

  -----------------------------------------------------------------------
  **Object**                          **Example**
  ----------------------------------- -----------------------------------
  Expense                             The View Hotel €128.62; payer = QA;
                                      split = 50/50

  Expense                             Balloon \$150; payer = QA; split =
                                      50/50

  Expense                             Railway £101.56; payer = Mia; split
                                      = 50/50

  Transfer                            QA → Mia £50.28 reimbursement

  Transfer                            Mia → QA £x repayment
  -----------------------------------------------------------------------

member_net = amount_paid_for_trip\
- member_cost_share\
+ transfers_received\
- transfers_sent\
\
Interpretation after normalizing all values to settlement currency:\
positive -\> member should receive\
negative -\> member should pay

UI phải hiển thị song song: total trip cost, cost share per person, paid
directly, transfers, remaining settlement. Không trộn transfer vào total
trip cost.

# 15. Reliability, caching, observability & cost control

  -----------------------------------------------------------------------
  **Area**                            **Requirement**
  ----------------------------------- -----------------------------------
  Freshness                           Every volatile provider snapshot
                                      has fetched_at and TTL.

  Caching                             Cache search/place/route results by
                                      normalized request; never cache
                                      booking guarantee beyond provider
                                      validity.

  Idempotency                         Create expense/transfer/booking
                                      mutations support idempotency key.

  Tracing                             One trace_id per plan generation;
                                      log provider calls and validator
                                      outcomes.

  LLM cost                            Use structured, bounded context; do
                                      not send whole trip history when
                                      scope is one day.

  Fallback                            Provider failure returns degraded
                                      state and stale-data label, not
                                      fabricated result.

  Rate limits                         Central provider client with
                                      retry/backoff and budget quotas.
  -----------------------------------------------------------------------

# 16. Testing strategy

  -----------------------------------------------------------------------
  **Test layer**                      **Examples**
  ----------------------------------- -----------------------------------
  Unit                                split formulas, score functions,
                                      time-window validator, lock rules

  Contract                            provider fixture -\> normalized
                                      model

  Integration                         trip create -\> generate -\>
                                      regenerate -\> settlement

  Golden scenarios                    Egypt scenario; late arrival;
                                      weather-sensitive balloon; removed
                                      day trip

  Property-based                      expense splits always sum to
                                      expense; settlement balances to
                                      zero

  Evals                               itinerary feasibility, explanation
                                      quality, food match explanation
                                      grounding

  UI                                  critical flows: create trip, choose
                                      flight, edit day, add expense
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------
  **Build gate ---** Không coi feature "done" chỉ vì model generate được
  output đẹp. Phải pass deterministic validators và tests.
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------

# 17. Deployment & environments

  -----------------------------------------------------------------------
  **Environment**                     **Purpose**
  ----------------------------------- -----------------------------------
  local                               Developer laptop; mock providers by
                                      default

  dev                                 Shared integration; sandbox/test
                                      provider credentials

  staging                             Production-like DB + provider
                                      quotas; seeded test trips

  prod                                Live users; strict secrets,
                                      backups, monitoring
  -----------------------------------------------------------------------

Recommended initial deployment: web on Vercel or equivalent; API on
managed container platform; PostgreSQL managed service with PostGIS.
Exact vendors are implementation decisions, not domain dependencies.

# 18. Modular repository & context-management rules

trip-companion/\
AGENTS.md\
README.md\
docs/\
PRODUCT.md\
ARCHITECTURE.md\
MODULES.md\
DECISIONS.md\
AI_HANDOFF.md\
apps/web/\
services/api/\
app/domain/\
trips/\
itinerary/\
recommendations/\
knowledge/\
expenses/\
app/providers/\
flights/\
places/\
routes/\
app/orchestration/\
packages/contracts/\
tests/

Một model/session mới chỉ cần đọc: AGENTS.md → module README → shared
contract liên quan → issue hiện tại. Không load toàn repo nếu task không
cần.

  -----------------------------------------------------------------------
  **Rule**                            **Implementation**
  ----------------------------------- -----------------------------------
  One issue = one context-safe task   Ví dụ FLIGHT-001, ITIN-003,
                                      FOOD-002

  No cross-module imports by          Use contracts/domain service
  convenience                         boundary

  Decision log mandatory              Architecture change -\>
                                      docs/DECISIONS.md

  Handoff file                        Update current state, next safe
                                      task, known blockers

  Small PRs                           Prefer \< \~400 changed lines when
                                      practical

  Fixtures                            Provider responses stored as
                                      sanitized fixtures for reproducible
                                      tests
  -----------------------------------------------------------------------

# 19. Roadmap, milestones & acceptance gates

  ------------------------------------------------------------------------------------
  **Milestone**           **Deliverable**                      **Exit criterion**
  ----------------------- ------------------------------------ -----------------------
  M0 --- Documentation &  PRD/architecture/schema/contracts;   All open architecture
  contracts               scaffold; CI/test baseline           questions tagged; core
                                                               Pydantic/TS contracts
                                                               agreed.

  M1 --- Trip workspace   Create/edit trip, members,           Can persist and reload
                          preferences, constraints, bookings   Egypt reference trip
                                                               without AI.

  M2 --- Places + routing Place search/details + normalized    Can calculate feasible
                          routes + candidate clustering        day candidates with
                                                               travel times.

  M3 --- Itinerary engine Generate/edit/lock/partial           Remove Aswan and
                          regenerate + validators              regenerate only 6 Nov
                                                               without touching other
                                                               days.

  M4 --- Flight search    Provider adapter + search UI +       Selected
                          selected flight constraint           arrival/departure
                                                               changes day capacity
                                                               correctly.

  M5 --- Contextual       Knowledge cards, taste engine, food  Recommendations show
  recommendation          ranking, photo spots                 provenance + why-match;
                                                               no sensitive inference.

  M6 --- Budget &         Multi-currency                       Egypt expense case
  settlement              expense/split/transfer/settlement    reconciles without
                                                               double counting
                                                               transfers.

  M7 --- During-trip mode Today, skip/late/replan, nearby      User can modify today
                          fallback                             from phone with minimal
                                                               steps.

  M8 --- Hardening        Observability, evals, security,      Staging passes golden
                          caching, quota control               scenarios and
                                                               failure-mode tests.
  ------------------------------------------------------------------------------------

# 20. Issue breakdown for modular implementation

  -----------------------------------------------------------------------
  **Issue**                           **Task**
  ----------------------------------- -----------------------------------
  DOC-001                             Freeze v0.1 PRD and decision log
                                      template

  CORE-001                            Define Trip, Member, Constraint
                                      schemas

  CORE-002                            Postgres migrations for core trip
                                      tables

  FLIGHT-001                          Normalized flight contract

  FLIGHT-002                          Mock provider + fixtures

  FLIGHT-003                          Live provider adapter

  PLACE-001                           Normalized place contract

  PLACE-002                           Google Places adapter

  ROUTE-001                           Route matrix adapter

  ITIN-001                            Candidate day builder

  ITIN-002                            Feasibility validator

  ITIN-003                            Locked items + partial regeneration

  AI-001                              Structured itinerary output schema

  AI-002                              Planner orchestration

  FOOD-001                            TasteProfile schema

  FOOD-002                            Review signal extractor

  FOOD-003                            Restaurant ranker + explanation

  KNOW-001                            Knowledge card schema + generation

  PHOTO-001                           PhotoSpot schema + curation API

  BUD-001                             Expense + split model

  BUD-002                             Transfers + settlement engine

  UI-001                              Create Trip flow

  UI-002                              Itinerary editor

  UI-003                              Today view

  QA-001                              Egypt golden scenario

  OPS-001                             Tracing + provider metrics
  -----------------------------------------------------------------------

# 21. Risks & mitigations

  -----------------------------------------------------------------------
  **Risk**                **Impact**              **Mitigation**
  ----------------------- ----------------------- -----------------------
  Provider access/pricing High                    Adapter interface +
  changes                                         mock provider +
                                                  multiple candidate
                                                  providers

  Google Maps/Places      High                    Keep
  terms by region                                 presentation/provider
                                                  boundaries; legal/terms
                                                  review before launch

  LLM hallucinates        High                    Structured output +
  schedule/facts                                  retrieval +
                                                  deterministic validator

  Review data too sparse  Medium                  Use first-party
                                                  feedback and restaurant
                                                  metadata; confidence
                                                  score

  Personalization becomes High                    Explicit taste vectors;
  stereotype                                      prohibit demographic
                                                  inference

  Trip edits cascade      High                    Plan versioning +
  unpredictably                                   dependency-aware
                                                  partial regeneration

  FX drift changes        Medium                  Store FX rate/timestamp
  historic budgets                                for finalized expense
                                                  view

  Context overload for AI Medium                  Module docs, issue
  coding                                          scopes, handoff file,
                                                  small PRs
  -----------------------------------------------------------------------

# 22. Open decisions

  -----------------------------------------------------------------------
  **ID**                  **Decision needed**     **Default until
                                                  decided**
  ----------------------- ----------------------- -----------------------
  D-01                    Auth provider           Use simple email/OAuth
                                                  abstraction; do not
                                                  bind domain to vendor

  D-02                    Primary map rendering   Keep separate from
                          provider                place data adapter;
                                                  verify EEA terms before
                                                  production

  D-03                    Flight provider for MVP Prototype adapter with
                                                  mock; choose live
                                                  provider after
                                                  access/cost check

  D-04                    Vector search           Do not add until
                          requirement             semantic retrieval
                                                  materially outperforms
                                                  relational filters

  D-05                    Long-term photo spot    Start curated; add user
                          sourcing                submissions after
                                                  moderation flow exists

  D-06                    FX source               Provider adapter;
                                                  finalized expenses can
                                                  freeze chosen
                                                  historical rate
  -----------------------------------------------------------------------

# 23. Definition of Done

-   Feature có issue và acceptance criteria.

-   Domain contract/schema được update trước hoặc cùng PR.

-   No provider-specific payload leaks beyond adapter boundary.

-   Unit/integration tests cho happy path + failure case.

-   AI output có schema validation và deterministic post-validator nếu
    liên quan itinerary/recommendation.

-   User-visible live data có source/freshness handling.

-   Privacy rules không bị phá, đặc biệt food personalization.

-   Docs/AI_HANDOFF.md được update nếu task thay state hoặc tạo blocker.

-   Golden Egypt scenario vẫn pass nếu change ảnh hưởng
    itinerary/budget.

# 24. References

  -------------------------------------------------------------------------------------------------------------------------------------
  **Reference**           **URL**                                                                               **Why it matters**
  ----------------------- ------------------------------------------------------------------------------------- -----------------------
  Skyscanner Flights Live https://developers.skyscanner.net/docs/flights-live-prices/overview                   Live search uses
  Prices API --- Overview                                                                                       create/poll workflow
                                                                                                                for route/date
                                                                                                                searches.

  Google Places API (New) https://developers.google.com/maps/documentation/places/web-service/quick-reference   Text/Nearby Search,
  --- Quick reference                                                                                           Place Details, Place
                                                                                                                Photos, regional/EEA
                                                                                                                notes.

  Google Routes API ---   https://developers.google.com/maps/documentation/routes/quick-reference               Compute Routes and
  Quick reference                                                                                               Compute Route Matrix.

  Duffel API --- Offers   https://duffel.com/docs/api/offers                                                    Offers may
                                                                                                                expire/change; refresh
                                                                                                                before booking.

  OpenAI API ---          https://developers.openai.com/api/docs/guides/structured-outputs                      Use schema-constrained
  Structured model                                                                                              outputs for
  outputs                                                                                                       planner/orchestration
                                                                                                                contracts.
  -------------------------------------------------------------------------------------------------------------------------------------

*Verification date for external references: 23 Nov 2026.*

  -----------------------------------------------------------------------
  **Next action after review ---** Freeze v0.1, split this document into
  repo-native Markdown docs (PRODUCT, ARCHITECTURE, MODULES, DECISIONS),
  then start M0 contracts/scaffold. Không bắt đầu provider integration
  trước khi D-02/D-03 có quyết định tạm thời.
  -----------------------------------------------------------------------

  -----------------------------------------------------------------------
