'use client';
"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
var _a;
Object.defineProperty(exports, "__esModule", { value: true });
exports.default = HumanReviewControls;
var react_1 = require("react");
var lucide_react_1 = require("lucide-react");
var API_BASE_URL = (_a = process.env.NEXT_PUBLIC_API_BASE_URL) !== null && _a !== void 0 ? _a : "http://localhost:8000/api";
function HumanReviewControls(_a) {
    var _b = _a.sessionId, sessionId = _b === void 0 ? "sample-session" : _b, _c = _a.answerId, answerId = _c === void 0 ? "a1" : _c, _d = _a.draftAnswer, draftAnswer = _d === void 0 ? "I solved a hard technical problem by breaking it into smaller pieces, validating each part, and collaborating with stakeholders to ensure alignment." : _d;
    var _e = (0, react_1.useState)(false), isEditing = _e[0], setIsEditing = _e[1];
    var _f = (0, react_1.useState)(draftAnswer), editedAnswer = _f[0], setEditedAnswer = _f[1];
    var _g = (0, react_1.useState)(null), statusMessage = _g[0], setStatusMessage = _g[1];
    var _h = (0, react_1.useState)(null), errorMessage = _h[0], setErrorMessage = _h[1];
    var _j = (0, react_1.useState)("pending"), currentStatus = _j[0], setCurrentStatus = _j[1];
    function submitReview(action, editedAnswerValue) {
        return __awaiter(this, void 0, void 0, function () {
            var response, payload_1, payload, error_1;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        setStatusMessage("Saving review action...");
                        setErrorMessage(null);
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 6, , 7]);
                        return [4 /*yield*/, fetch("".concat(API_BASE_URL, "/review"), {
                                method: "POST",
                                headers: {
                                    "Content-Type": "application/json",
                                },
                                body: JSON.stringify({
                                    session_id: sessionId,
                                    answer_id: answerId,
                                    action: action,
                                    edited_answer: editedAnswerValue,
                                }),
                            })];
                    case 2:
                        response = _b.sent();
                        if (!!response.ok) return [3 /*break*/, 4];
                        return [4 /*yield*/, response.json().catch(function () { return null; })];
                    case 3:
                        payload_1 = _b.sent();
                        throw new Error((_a = payload_1 === null || payload_1 === void 0 ? void 0 : payload_1.detail) !== null && _a !== void 0 ? _a : "Unable to submit review action.");
                    case 4: return [4 /*yield*/, response.json()];
                    case 5:
                        payload = _b.sent();
                        setCurrentStatus(payload.human_status);
                        setStatusMessage(payload.message);
                        setIsEditing(false);
                        return [3 /*break*/, 7];
                    case 6:
                        error_1 = _b.sent();
                        setStatusMessage(null);
                        setErrorMessage(error_1 instanceof Error ? error_1.message : "Review action failed.");
                        return [3 /*break*/, 7];
                    case 7: return [2 /*return*/];
                }
            });
        });
    }
    function handleApprove() {
        submitReview("approve");
    }
    function handleRequestRevision() {
        submitReview("request_revision");
    }
    function handleSaveEdit() {
        if (!editedAnswer.trim()) {
            setErrorMessage("Edited answer cannot be empty.");
            return;
        }
        submitReview("edit", editedAnswer.trim());
    }
    return (<section className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Human Review</h2>
          <p className="text-sm text-muted-foreground">
            Review draft answers by approving them, editing final text, or requesting revision.
          </p>
          <p className="mt-2 text-sm">
            <span className="font-medium">Current status:</span> {currentStatus}
          </p>
          {statusMessage ? (<p className="mt-1 text-sm text-green-700">{statusMessage}</p>) : null}
          {errorMessage ? (<p className="mt-1 text-sm text-red-700">{errorMessage}</p>) : null}
        </div>

        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={function () { return setIsEditing(!isEditing); }} className="inline-flex min-h-10 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium">
            <lucide_react_1.MessageSquare className="size-4" aria-hidden="true"/>
            {isEditing ? "Cancel Edit" : "Edit"}
          </button>
          <button type="button" onClick={handleRequestRevision} className="inline-flex min-h-10 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium">
            <lucide_react_1.X className="size-4" aria-hidden="true"/>
            Request Revision
          </button>
          <button type="button" onClick={handleApprove} className="inline-flex min-h-10 items-center gap-2 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground">
            <lucide_react_1.Check className="size-4" aria-hidden="true"/>
            Approve
          </button>
        </div>
      </div>

      {isEditing ? (<div className="mt-4">
          <label className="mb-2 block text-sm font-medium text-foreground">Edit final answer</label>
          <textarea className="w-full rounded-md border border-border bg-background p-3 text-sm text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-primary" rows={6} value={editedAnswer} onChange={function (event) { return setEditedAnswer(event.target.value); }}/>
          <div className="mt-3 flex items-center gap-2">
            <button type="button" onClick={handleSaveEdit} className="inline-flex min-h-10 items-center gap-2 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground">
              Save Edit
            </button>
            <button type="button" onClick={function () {
                setEditedAnswer(draftAnswer);
                setIsEditing(false);
                setErrorMessage(null);
            }} className="inline-flex min-h-10 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium">
              Cancel
            </button>
          </div>
        </div>) : null}
    </section>);
}
