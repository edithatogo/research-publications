// Typed structured PubMed assertions only. This does not acquire or hash raw XML.
(Rows as table) as table =>
let
    Valid = List.AllTrue(List.Transform(Table.ToRecords(Rows), (R) =>
        R[SourceProvider] = "PubMed" and R[ReviewState] = "Not reviewed"
        and R[AuthenticationState] = "Not authenticated"
        and Value.Is(R[StructuredMetadataSHA256], type text)
        and Text.Length(R[StructuredMetadataSHA256]) = 64
        and (R[RawSHA256] = null or R[RawSHA256] = "")
        and R[CanonicalAdmission] = false and R[IdentityQualified] = false)),
    Result = if Valid then Rows else error "Unqualified structured PubMed provenance"
in
    Result
