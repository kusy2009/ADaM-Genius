/**
@file adamgenius.sas
@brief 
@details


@param adamvar Description of adamvar
@param adamigversion Description of adamigversion
@param adamctversion Description of adamctversion


@return 
@version 1.0
@author 













@maintenance 2025-04-24: Initial implementation []
*/

%macro adamgenius(adamvar=, adamigversion=, adamctversion=);

	/*----------------------------------------------------------------------------------------------------------/
	    If user does not explicitly provide an adamIG version, fetch the latest from the CDISC Library
	/----------------------------------------------------------------------------------------------------------*/
	%if %superq(adamigversion)= %then %do;
	
	    /*----------------------------------------------------------------------------------------------------------/
	        1) Retrieve all adamIG products from the Library
	    /----------------------------------------------------------------------------------------------------------*/
	    filename main TEMP;
	    proc http
	        url="https://library.cdisc.org/api/mdr/products"
	        method="GET"
	        out=main;
	        headers
	            "api-key"="&cdiscapikey" 
	            "Accept"="application/json"; 
	    run;
	
	    libname main json fileref=main;
	
	    /*----------------------------------------------------------------------------------------------------------/
	        2) Filter only the 'Human Clinical' adamIG entries and parse out the version from the href
	    /----------------------------------------------------------------------------------------------------------*/
	    data filtered_data;
	        set main._links_adam;
	        if index(upcase(href), 'ADAMIG') > 0;
	        adamigversion = substr(href, 18); 
	    run;
	
	    proc sort data=filtered_data;
	        by descending adamigversion;
	    run;
	
	    /*----------------------------------------------------------------------------------------------------------/
	        3) Keep only the highest (latest) version
	    /----------------------------------------------------------------------------------------------------------*/
	    data latest_version;
	        set filtered_data;
	        if _N_ = 1; 
	    run;
	
	    /*----------------------------------------------------------------------------------------------------------/
	        4) Assign macro variable &adamigversion to this latest version
	    /----------------------------------------------------------------------------------------------------------*/
	    proc sql noprint;
	        select adamigversion into :adamigversion trimmed
	        from latest_version;
	    quit;
	
	    %put NOTE: (adamgenius) Automatically fetched adamIG version = &adamigversion;
	
	%end;

    /*----------------------------------------------------------------------------------------------------------/
        Temporary file reference for the adam JSON metadata
    /----------------------------------------------------------------------------------------------------------*/
    filename adam TEMP;
  
    proc http
        url="https://library.cdisc.org/api/mdr/adam/adamig-&adamigversion"
        method="GET"
        out=adam;
        headers
            "api-key"="&cdiscapikey" 
            "Accept"="application/json"; 
    run;

    libname adam json fileref=adam;

    /*----------------------------------------------------------------------------------------------------------/
        Dataset Sheet
    /----------------------------------------------------------------------------------------------------------*/
	data dataset_sheet;
	retain Dataset Description Class Purpose;
	set adam.DATASTRUCTURES(in=b drop=description rename=(name=Dataset label=Description));
		Purpose="Analysis";
	keep Dataset Description Class Purpose;
	run;

    /*----------------------------------------------------------------------------------------------------------/
        Variable Sheet
    /----------------------------------------------------------------------------------------------------------*/
	/*Fetch Dataset Names*/
	proc sql;
	    create table format_data as
	    select distinct 
	        ordinal_analysisVariableSets as start,
	        case
	            when substr(label, 1, 4) = "ADSL" then "ADSL"
	            else "BDS"
	        end as label,
			"adamfmt" as fmtname 
	    from adam.DATASTRUCTURES_ANALYSISVARIABL;
	quit;
	
	proc format cntlin=format_data;
	run;
	
	/*Fetch Codelist*/
	proc sql;
	    create table cd_format_data as
	    select distinct 
	        ordinal_analysisVariables as start,
	        codelistSubmissionValues1 as label,
			"adamcdfmt" as fmtname 
	    from adam.ANALYSISVARIABLES_CODELISTSUBM;
	quit;
	
	proc format cntlin=cd_format_data;
	run;
	
	data Variable_sheet;
	set adam.ANALYSISVARI_ANALYSISVARIABLES(in=b drop=description rename=(name=Variable simpleDatatype=DataType));
		length Dataset  $10 formatted_codelist Codelist $200;
		 Dataset = strip(put(ordinal_analysisVariableSets, adamfmt.));    
		 /* Apply Codelist Format and Handle Missing Values */
	    formatted_codelist = put(ordinal_analysisVariables, adamcdfmt.);
	
	    if formatted_codelist =: ' ' then call missing(Codelist); /* If unmatched, set to blank */
	    else Codelist = strip(formatted_codelist);
	
	run;

    /*----------------------------------------------------------------------------------------------------------/
        Identify which dataset the &adamvar belongs to
    /----------------------------------------------------------------------------------------------------------*/
    proc sql noprint;
        select strip(compbl(dataset)) into: dataset trimmed 
        from Variable_sheet
        where variable="&adamvar";
    quit;

    %PUT NOTE: Dataset resolved to &dataset;

    /*----------------------------------------------------------------------------------------------------------/
        If we cannot find the dataset, abort the macro
    /----------------------------------------------------------------------------------------------------------*/
    %if %length(&dataset)=0 %then %do;
        %put NOTE: Aborting macro since dataset is missing. Please check input variable &adamvar and update;
        %return;
    %end; 
    %else %do;

        /*----------------------------------------------------------------------------------------------------------/
            Get details of the variable from the API
        /----------------------------------------------------------------------------------------------------------*/
        filename varcheck TEMP;
        proc http
            url="https://library.cdisc.org/api/mdr/adam/adamig-&adamigversion/datastructures/&dataset/variables/&adamvar"
            method="GET"
            out=varcheck;
            headers
                "api-key"="&cdiscapikey"
                "Accept"="application/json";
        run;

        libname varcheck JSON fileref=varcheck;
        
        data varinfo;
            set varcheck.alldata;
            keep p1 value;
            if p2='parentDataset' and p3='title' then p1='DatasetLabel';
            if p1 ne '_links';
            if not missing(value);
        run;

        /*----------------------------------------------------------------------------------------------------------/
            Print variable info
        /----------------------------------------------------------------------------------------------------------*/
        title "Details of CDISC adam variable &dataset..&adamvar (adam IG Version=&adamigversion)";
        proc print data=varinfo noobs label;
            var p1 value;
            label p1 = "Parameter" 
                  value="Value";
        run;
        title;

        /*----------------------------------------------------------------------------------------------------------/
            Extract Codelist Values (could be multiple)
        /----------------------------------------------------------------------------------------------------------*/
        %let codelistValue=;

        proc sql noprint;
            select distinct strip(scan(value, -1))
            into :codelistValue separated by ' '
            from varcheck.alldata
            where index(upcase(p2), "CODELIST") > 0 
              and p3 = "href";
        quit;
        
        %put NOTE: Extracted CODELIST = &codelistValue;

        /*----------------------------------------------------------------------------------------------------------/
            If no codelist is present, exit 
        /----------------------------------------------------------------------------------------------------------*/
        %if %length(&codelistValue)=0 %then %do;
            %put NOTE: CODELIST is not present for this variable;
            %return;
        %end;

        /*----------------------------------------------------------------------------------------------------------/
            If at least one codelist is present, call %GetCDISCCodelist for each
        /----------------------------------------------------------------------------------------------------------*/
        %else %if %length(&codelistValue)>0 %then %do;
            
            /*--------------------------------------------------------------------------------*/
            /*    Macro to retrieve the CDISC CT for a given single codelistValue             */
            /*    (slightly updated to accept codelistValue as a parameter)                   */
            /*--------------------------------------------------------------------------------*/
            %macro GetCDISCCodelist(
                codelistValue=,
                codelistType=CodelistCode,  /* Match by ID or CodelistCode */
                standard=adam,              /* Default to adam */
                outlib=WORK                /* Output Library */
            );
            
                /*----------------------------------------------------------------------------------------------------------/
                    Validate input
                /----------------------------------------------------------------------------------------------------------*/
                %if %superq(codelistValue)= %then %do;
                    %put ERROR: You must specify a codelistValue= (e.g., C120523 for EGTESTCD etc);
                    %return;
                %end;
            
                /*----------------------------------------------------------------------------------------------------------/
                    Ensure correct standard input
                /----------------------------------------------------------------------------------------------------------*/
                %let valid_standards = SDTM ADAM CDASH DEFINE-XML SEND DDF GLOSSARY MRCT PROTOCOL QRS QS-FT TMF;
                %if not (%sysfunc(indexw(&valid_standards, %upcase(&standard)))) %then %do;
                    %put ERROR: Invalid standard "&standard". Supported values are:;
                    %put ERROR: &valid_standards;
                    %return;
                %end;
            
                /*----------------------------------------------------------------------------------------------------------/
                    Convert standard to API format
                /----------------------------------------------------------------------------------------------------------*/
                %let api_standard = %lowcase(&standard)ct;
            
                /*----------------------------------------------------------------------------------------------------------/
                    Dynamically fetch available versions if not provided
                /----------------------------------------------------------------------------------------------------------*/
                %if %superq(adamctversion)= %then %do;
                    %put NOTE: Version is not specified. Fetching the latest version...;
            
                    filename version TEMP;
                    proc http
                        url="https://api.library.cdisc.org/api/mdr/products/Terminology"
                        method="GET"
                        out=version;
                        headers
                            "api-key"="&cdiscapikey"
                            "Accept"="application/json";
                    run;
            
                    libname version JSON fileref=version;
                    
                    data versions;
                        set version._LINKS_PACKAGES;
                        /* Extract the standard from href, remove '/package.json' at the end */
                        standard_from_href = scan(href, 4, '/'); 
                        standard_from_href = substr(standard_from_href, 1, length(standard_from_href)-13);
                        if upcase(standard_from_href)=upcase("&standard");
                        
                        /* Extract the date (YYYY-MM-DD) from the href field */           
                        version_date = substr(href, length(href)-9, 10);
                        keep version_date standard_from_href;
                    run;
                    
                    proc sort data=versions;
                        by descending version_date;
                    run;
                    
                    data _null_;
                        set versions(obs=1);
                        call symputx('adamctversion', version_date);
                    run;
            
                    %put NOTE: Latest &standard CT version is &adamctversion;
                %end;
            
                /*----------------------------------------------------------------------------------------------------------/
                    Fetch the specific standard CT package
                /----------------------------------------------------------------------------------------------------------*/
                filename cdiscCT TEMP;
                proc http
                    url="https://api.library.cdisc.org/api/mdr/ct/packages/&api_standard.-&adamctversion."
                    method="GET"
                    out=cdiscCT;
                    headers
                        "api-key"="&cdiscapikey"
                        "Accept"="application/json";
                run;
            
                libname cdisc JSON fileref=cdiscCT;
            
                /*----------------------------------------------------------------------------------------------------------/
                    Extract Codelist-level data
                /----------------------------------------------------------------------------------------------------------*/
                data _codelist_data;
                    retain submissionValue conceptId name extensible ordinal_codelists;
                    set cdisc.CODELISTS(keep=conceptId submissionValue extensible name ordinal_codelists);
                    rename 
                        conceptId       = CodelistCode
                        submissionValue = ID;
                run;
            
                /*----------------------------------------------------------------------------------------------------------/
                    Extract Term-level data
                /----------------------------------------------------------------------------------------------------------*/
                data _codelist_terms_data;
                    retain submissionValue conceptId preferredTerm ordinal_codelists;
                    set cdisc.CODELISTS_TERMS(keep=ordinal_codelists conceptId submissionValue preferredTerm);
                    rename 
                        submissionValue = TERM
                        conceptId       = TermCode
                        preferredTerm   = DecodedValue;
                run;
            
                /*----------------------------------------------------------------------------------------------------------/
                    Merge codelist and terms
                /----------------------------------------------------------------------------------------------------------*/
                proc sql;
                    create table &outlib..merged_codelists as
                    select 
                        a.*,
                        b.TermCode,
                        b.TERM,
                        b.DecodedValue as TermDecodedValue
                    from _codelist_data as a
                    inner join _codelist_terms_data as b
                    on a.ordinal_codelists = b.ordinal_codelists
                    order by a.ID, b.TERM;
                quit;
            
                proc format;
                    value $extensible_fmt
                        "true"  = "Yes"
                        "false" = "No";
                run;
            
                /*----------------------------------------------------------------------------------------------------------/
                    Filter for the specific codelist
                /----------------------------------------------------------------------------------------------------------*/
                data &outlib..specific_codelist;
                    set &outlib..merged_codelists;
                    length ExtensibleYN $3;
                    ExtensibleYN = put(Extensible, $extensible_fmt.);
                
                    %if %upcase(&codelistType)=ID %then %do;
                        where upcase(ID) = upcase("&codelistValue");
                    %end;
                    %else %if %upcase(&codelistType)=CODELISTCODE %then %do;
                        where upcase(CodelistCode) = upcase("&codelistValue");
                    %end;
                run;
            
                /*----------------------------------------------------------------------------------------------------------/
                    Check if codelist exists
                /----------------------------------------------------------------------------------------------------------*/
                proc sql noprint;
                    select count(*) into: check_exists
                    from &outlib..specific_codelist;
                    select distinct ExtensibleYN into: Extensible
                    from &outlib..specific_codelist;
                quit;
            
                /*----------------------------------------------------------------------------------------------------------/
                    If not found in adam ct, print from sdtm ct and exit
                /----------------------------------------------------------------------------------------------------------*/
                %if &check_exists = 0 %then %do;
                    %put ALERT: The provided Codelist Value "&codelistValue" does not exist in the &standard Controlled Terminology version &adamctversion.;
                    %put ALERT: Submission values listed from SDTM Codelists;
                    
                                    /*----------------------------------------------------------------------------------------------------------/
					                    Fetch the specific standard CT package
					                /----------------------------------------------------------------------------------------------------------*/
					                filename sdtmct TEMP;
					                proc http
					                    url="https://api.library.cdisc.org/api/mdr/ct/packages/sdtmct-&adamctversion."
					                    method="GET"
					                    out=sdtmct;
					                    headers
					                        "api-key"="&cdiscapikey"
					                        "Accept"="application/json";
					                run;
					            
					                libname cdisc JSON fileref=sdtmct;
					            
					                /*----------------------------------------------------------------------------------------------------------/
					                    Extract Codelist-level data
					                /----------------------------------------------------------------------------------------------------------*/
					                data _codelist_data;
					                    retain submissionValue conceptId name extensible ordinal_codelists;
					                    set cdisc.CODELISTS(keep=conceptId submissionValue extensible name ordinal_codelists);
					                    rename 
					                        conceptId       = CodelistCode
					                        submissionValue = ID;
					                run;
					            
					                /*----------------------------------------------------------------------------------------------------------/
					                    Extract Term-level data
					                /----------------------------------------------------------------------------------------------------------*/
					                data _codelist_terms_data;
					                    retain submissionValue conceptId preferredTerm ordinal_codelists;
					                    set cdisc.CODELISTS_TERMS(keep=ordinal_codelists conceptId submissionValue preferredTerm);
					                    rename 
					                        submissionValue = TERM
					                        conceptId       = TermCode
					                        preferredTerm   = DecodedValue;
					                run;
					            
					                /*----------------------------------------------------------------------------------------------------------/
					                    Merge codelist and terms
					                /----------------------------------------------------------------------------------------------------------*/
					                proc sql;
					                    create table &outlib..merged_codelists as
					                    select 
					                        a.*,
					                        b.TermCode,
					                        b.TERM,
					                        b.DecodedValue as TermDecodedValue
					                    from _codelist_data as a
					                    inner join _codelist_terms_data as b
					                    on a.ordinal_codelists = b.ordinal_codelists
					                    order by a.ID, b.TERM;
					                quit;
					            
					                proc format;
					                    value $extensible_fmt
					                        "true"  = "Yes"
					                        "false" = "No";
					                run;
					            
					                /*----------------------------------------------------------------------------------------------------------/
					                    Filter for the specific codelist
					                /----------------------------------------------------------------------------------------------------------*/
					                data &outlib..specific_codelist;
					                    set &outlib..merged_codelists;
					                    length ExtensibleYN $3;
					                    ExtensibleYN = put(Extensible, $extensible_fmt.);
					                
					                    %if %upcase(&codelistType)=ID %then %do;
					                        where upcase(ID) = upcase("&codelistValue");
					                    %end;
					                    %else %if %upcase(&codelistType)=CODELISTCODE %then %do;
					                        where upcase(CodelistCode) = upcase("&codelistValue");
					                    %end;
					                run;
					                
					                proc sql noprint;
					                    select count(*) into: check_exists
					                    from &outlib..specific_codelist;
					                    select distinct ExtensibleYN into: Extensible
					                    from &outlib..specific_codelist;
					                quit;
                                    /*----------------------------------------------------------------------------------------------------------/
					                    If not found, print warning and exit
					                /----------------------------------------------------------------------------------------------------------*/
					                %if &check_exists = 0 %then %do;
					                    %put WARNING: The provided Codelist Value "&codelistValue" does not exist in both SDTM and &standard Controlled Terminology version &adamctversion.;
					                    %put WARNING: Please check if your ID is correct or if it exists in the &standard Codelists.;
					                    title "Codelist Value Not Found";
					                    data _null_;
					                        file print;
					                        put "------------------------------------------------------------";
					                        put "WARNING: The specified Codelist Value '&codelistValue' was not found in &standard CT Version &sdtmctversion.";
					                        put "Please verify your input value.";
					                        put "------------------------------------------------------------";
					                    run;
					                    title;
					                    %return;
					                %end;                
              
                    	title "Submission Values for &codelistType=&codelistValue (SDTM CT Version=&adamctversion, Extensible=&Extensible)";
		                proc print data=&outlib..specific_codelist noobs label;
		                    var TERM termdecodedvalue;
		                    label TERM = "Submission Value" 
		                          termdecodedvalue="Decoded Value";
		                run;
		                title;
                    %return;
                %end;
            
                /*----------------------------------------------------------------------------------------------------------/
                    Output results
                /----------------------------------------------------------------------------------------------------------*/
                title "Submission Values for &codelistType=&codelistValue (&standard. CT Version=&adamctversion, Extensible=&Extensible)";
                proc print data=&outlib..specific_codelist noobs label;
                    var TERM termdecodedvalue;
                    label TERM = "Submission Value" 
                          termdecodedvalue="Decoded Value";
                run;
                title;
            
            %mend GetCDISCCodelist;

            /*----------------------------------------------------------------------------------------------------------/
               We now split &codelistValue by spaces and call %GetCDISCCodelist 
               once for each separate value
            /----------------------------------------------------------------------------------------------------------*/
            %local i singleCode;
            %let i=1;
            %do %while(%scan(&codelistValue,&i,%str( )) ne %str());
                %let singleCode=%scan(&codelistValue,&i,%str( ));
                /* Call macro for each codelist value */
                %GetCDISCCodelist(codelistValue=&singleCode);
                %let i=%eval(&i+1);
            %end;

        %end; /* end of multiple codelist logic */
    %end; /* end of else for dataset existence */

%mend adamgenius;