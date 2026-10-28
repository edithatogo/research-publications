// Consumer of an independently qualified typed producer. No acquisition/hash API.
(Rows as table, Expected as record, PubMedTyped as function, Canonical as table) as table =>
let
    TextFields = {"AssertionRevisionKey","ProjectionID","EvidenceKey","RelationshipKind","SourceWorkID","PublicationDOI","PublicationPMID","ReferenceType","FromKey","ToKey","FromLabel","ToLabel","ORCID","ORCIDStatus","ROR","IdentityStatus","SourceURL","ObservedUTC","RawSHA256","StructuredMetadataSHA256","SourceVersion","ReviewState","AuthenticationState","SourceProvider","CanonicalKey","GenerationID","CanonicalSnapshotID","SourceSnapshotID","ProjectionRevisionSHA256","SourcePathsJSON","RawAssertionJSON"},
    LogicalFields = {"CandidateEligible","SourceRetracted","IdentityQualified","CanonicalAdmission","MutationAuthorized","NativeG06Admission"},
    Fields = TextFields & {"CanonicalMatchCount"} & LogicalFields,
    Shape = List.Sort(Table.ColumnNames(Rows)) = List.Sort(Fields),
    Captured = if Shape then Table.Buffer(Rows) else error "Typed candidate schema drift",
    CanonicalShape = List.Sort(Table.ColumnNames(Canonical)) = List.Sort(Expected[PublicationFields]),
    CanonicalKeys = if CanonicalShape then Table.Column(Canonical, "CanonicalKey") else error "Canonical field inventory drift",
    CanonicalValid = List.Count(CanonicalKeys) = Expected[PublicationCount]
        and List.Count(List.Distinct(CanonicalKeys,Comparer.OrdinalIgnoreCase)) = List.Count(CanonicalKeys)
        and List.Sort(CanonicalKeys) = List.Sort(Expected[CanonicalKeys]),
    Typed = List.AllTrue(List.Transform(Table.ToRecords(Captured), (R) =>
        List.AllTrue(List.Transform(TextFields, (F) => let V=Record.Field(R,F) in V=null or Value.Is(V,type text)))
        and List.AllTrue(List.Transform(LogicalFields, (F) => let V=Record.Field(R,F) in V=null or Value.Is(V,type logical)))
        and Value.Is(R[CanonicalMatchCount],type number) and R[CanonicalMatchCount]>=0
        and Number.RoundDown(R[CanonicalMatchCount])=R[CanonicalMatchCount]
        and Value.Is(R[CandidateEligible],type logical)
        and R[ProjectionID]=Expected[ProjectionID]
        and R[ReviewState]="Not reviewed" and R[AuthenticationState]="Not authenticated"
        and R[CanonicalAdmission]=false and R[IdentityQualified]=false
        and R[MutationAuthorized]=false and R[NativeG06Admission]=false
        and (R[SourceRetracted]<>true or R[CandidateEligible]=false)
        and (if R[CanonicalKey]<>null and R[CanonicalKey]<>"" then R[CanonicalMatchCount]=1 and List.Contains(CanonicalKeys,R[CanonicalKey]) else R[CanonicalMatchCount]<>1))),
    Unique = List.Count(List.Distinct(Table.Column(Captured,"AssertionRevisionKey")))=Table.RowCount(Captured),
    Checked = if CanonicalValid and Typed and Unique and Table.RowCount(Captured)=Expected[RowCount]
        then Captured else error "Candidate generation/type/cardinality drift",
    PubMed = PubMedTyped(Table.SelectRows(Checked,each [SourceProvider]="PubMed")),
    Other = Table.SelectRows(Checked,each [SourceProvider]<>"PubMed"),
    Combined = Table.Combine({Other,PubMed}),
    Result = Table.TransformColumnTypes(Combined,List.Transform(TextFields,each {_,type text}) & {{"CanonicalMatchCount",Int64.Type}} & List.Transform(LogicalFields,each {_,type logical}))
in
    Result
