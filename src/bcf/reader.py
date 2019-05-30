import sys
import os
import dateutil.parser
import util
import project
import viewpoint
from zipfile import ZipFile
from xmlschema import XMLSchema
from uuid import UUID
from typing import List, Dict
from uri import Uri
from modification import Modification
from markup import (Comment, Markup, Header, ViewpointReference)
from topic import (Topic, BimSnippet, DocumentReference)

DEBUG = True
SUPPORTED_VERSIONS = ["2.1"]

if DEBUG:
    import pprint

def readFile(path: str):

    """
    Tries to open the supplied file (`path`) and returns the ZipFile object.
    If an exception is raised `None` is returned.
    """

    if not os.path.exists(str):
        raise ValueError

    file = None
    try:
        file = ZipFile(path)
    except Exception as e:
        print("The supplied BCF file ({}) could not be opened.\nError:\
                {}".format(path, str(e)))
        return None

    return file


def schemaValidate(schemaPath: str, xmlFile: str):

    """
    Takes the schemaFile and loads it into the module xmlschema. With the
    resulting object `xmlFile` is checked whether it adheres to the
    specification or not.
    Returns a tuple: first element is a boolean value, and the second is a
    string containing the error message.
    """

    if not (os.path.exists(schemaPath) or os.path.exists(xmlFile)):
        raise ValueError

    schema = XMLSchema(schemaPath)
    valid = schema.is_valid(xmlFile)
    print("validating {} against {}".format(xmlFile, schemaPath))
    if valid:
        return (valid, "")
    else:
        try:
            # it is going to fail. I want the error message to return it
            schema.validate(xmlFile)
        except Exception as e:
            return (valid, str(e))


def extractFileToTmp(zipFilePath: str):

    """
    Extracts the zipFile to the temporary directory of the system.
    """

    zipFile = ZipFile(zipFilePath)

    extractionPath = str()
    if os.name == "nt":
        extractionPath = "C:\\Temp\\"
    else:
        extractionPath = "/tmp/"
    extractionPath += os.path.basename(zipFilePath)

    if DEBUG:
        print("Extracting {} to {}".format(zipFile.filename, extractionPath))
    zipFile.extractall(extractionPath)
    return extractionPath


def extractMemberToTmp(zipFile: ZipFile, memberName: str):

    """
    Tries to extract the file or directory with the name `memberName` from the
    given zipFile `zipFile` into a temporary directory. If successful the path
    to the file is returned, otherwise None is returned.
    """

    if not memberName in zipFile.namelist():
        raise FileNotFoundError("'{}' is not part of the supplied zip archive"\
            " {}. Make sure that it is a correct bcf"\
            " archive!".format(memberName, zipFile.filename))

    extractionPath = util.getSystemTmp()
    filePath = str()
    try:
        filePath = zipFile.extract(memberName, extractionPath)
    except Exception as e:
        print("Error during extracting '{}' to"\
                " {}".format(memberName, extractionPath))
        print("Make sure that '{}' exists exactly like that in the zipFile "\
                "and does not reside in any additional"\
                " subdirectory".format(memberName))
        return None

    return filePath


def getVersion(extrBcfPath: str, versionSchemaPath: str):

    """
    Tries to open `extrBcfPath`/bcf.version. If successful it parses it
    into a python dictonary and returns the content of the attribute
    `VersionId` of the element `Version`.

    If `bcf.version` was not found a ValueError is raised. If `bcf.version`
    does not parse against versionSchema then `None` is returned.
    """

    versionFileName = "bcf.version"
    versionFilePath = os.path.join(extrBcfPath, versionFileName)
    if not os.path.exists(versionFilePath):
        raise ValueError("{} was not found in the extracted zip archive {}."\
                "Make sure that you opened a correct bcf zip archive.".format(
                    versionFileName,
                    os.path.basename(extrBcfPath)))

    versionSchema = XMLSchema(versionSchemaPath)
    if not versionSchema.is_valid(versionFilePath):
        return None

    versionDict = versionSchema.to_dict(versionFilePath)
    if DEBUG:
        pprint.pprint(versionDict)
    return versionDict["@VersionId"]


def getFileListByExtension(topDir: str, extension: str):

    """
    Returns a list of files in the `topDir` directory that end with `extension`
    """

    fileList = [ f for f in os.listdir(topDir)
                    if os.path.isfile(os.path.join(topDir, f)) ]
    return list(filter(lambda f: f.endswith(extension), fileList))


def getOptionalFromDict(d: Dict, desiredValue: str, empty):

    if desiredValue in d:
        return d[desiredValue]
    return empty


########## Object builder functions ##########

def buildProject(projectFilePath: str, projectSchema: str):

    """
    Parses the contents of the project.bcfv file pointed to by
    `projectFilePath`.
    First the XML file is parsed into a python dictionary using
    xmlschema.XMLSchema.to_dict(xmlFilePath). Then this python dictionary is morphed
    into an objec of the Project class.

    This function assumes that project.bcfp was already successfully validated.
    """

    if projectFilePath is None or projectSchema is None:
        return None
    if not os.path.exists(projectFilePath):
        return None
    if not os.path.exists(projectSchema):
        return None

    schema = XMLSchema(projectSchema)
    projectDict = schema.to_dict(projectFilePath)

    # can do that because the project file is valid and ProjectId is required
    # by the schema
    pId = UUID(projectDict["Project"]["@ProjectId"])
    pName = str()
    pExtensionSchema = str()
    if "Name" in projectDict["Project"]:
        pName = projectDict["Project"]["Name"]
    if "ExtensionSchema" in projectDict:
        pExtensionSchema = projectDict["ExtensionSchema"]

    p = project.Project(pId, pName, pExtensionSchema)
    return p


def buildComment(commentDict: Dict):

    commentDate = dateutil.parser.parse(commentDict["Date"]) # parse ISO 8601 datetime
    commentAuthor = commentDict["Author"]
    creationData = Modification(commentAuthor, commentDate)

    modifiedAuthor = None
    modifiedDate = None
    modifiedData = None
    if ("ModifiedAuthor" in commentDict and
           "ModifiedDate" in commentDict):
        modifiedAuthor = commentDict["ModifiedAuthor"]
        modifiedDate = dateutil.parser.parse(commentDict["ModifiedDate"])
        modifiedData = Modification(modifiedAuthor, modifiedDate)

    commentString = commentDict["Comment"]

    viewpointRef = None
    """ TODO: Refactor viewpoint situation.
    if "Viewpoint" in commentDict:
        viewpointUUID = UUID(commentDict["Viewpoint"])
    """

    comment = Comment(creationData, commentString, viewpointRef, modifiedData)
    return comment


def buildBimSnippet(snippetDict: Dict):

    reference = Uri(snippetDict["Reference"])
    referenceSchema = Uri(snippetDict["ReferenceSchema"])
    snippetType = snippetDict["@SnippetType"]
    isExternal = getOptionalFromDict(snippetDict, "@isExternal", False)

    return BimSnippet(snippetType, isExternal, reference, referenceSchema)


def buildDocRef(docDict: Dict):

    docUri = getOptionalFromDict(docDict, "ReferencedDocument", None)
    if docUri: # envelope a uri string into an object of Uri
        docUri = Uri(docUri)

    docName = getOptionalFromDict(docDict, "Description", None)
    docId = getOptionalFromDict(docDict, "@Guid", None)
    if docId: #envelope a guid in an UUID object
        docId = UUID(docId)

    docExternal = getOptionalFromDict(docDict, "@isExternal", False)

    return DocumentReference(docId, docExternal, docUri, docName)


def buildTopic(topicDict: Dict):

    id = UUID(topicDict["@Guid"])
    title = topicDict["Title"]

    topicDate = dateutil.parser.parse(topicDict["CreationDate"])
    topicAuthor = topicDict["CreationAuthor"]
    creationData = Modification(topicAuthor, topicDate)

    topicStatus = getOptionalFromDict(topicDict, "@TopicStatus", "")
    topicType = getOptionalFromDict(topicDict, "@TopicType", "")
    topicPriority = getOptionalFromDict(topicDict, "Priority", "")

    modifiedDate = getOptionalFromDict(topicDict, "ModifiedDate", None)
    modifiedAuthor = getOptionalFromDict(topicDict, "ModifiedAuthor", None)
    modifiedData = None
    if not (modifiedDate is None or modifiedAuthor is None):
        modifiedData = Modification(modifiedAuthor, modifiedDate)

    index = getOptionalFromDict(topicDict, "Index", 0)
    dueDate = getOptionalFromDict(topicDict, "DueDate", None)
    if dueDate is not None:
        dueDate = dateutil.parser.parse(dueDate)

    assignee = getOptionalFromDict(topicDict, "AssignedTo", "")
    stage = getOptionalFromDict(topicDict, "State", "")
    description = getOptionalFromDict(topicDict, "Description", "")

    bimSnippet = None
    if "BimSnippet" in topicDict:
        bimSnippet = buildBimSnippet(topicDict["BimSnippet"])

    labelList = getOptionalFromDict(topicDict, "Labels", list())

    docRefList = getOptionalFromDict(topicDict, "DocumentReference", list())
    docRefs = [ buildDocRef(docRef) for docRef in docRefList ]

    relatedList = getOptionalFromDict(topicDict, "RelatedTopic", list())
    relatedTopics = [ UUID(relTopic["@Guid"]) for relTopic in relatedList ]

    topic = Topic(id, title, creationData,
            topicType, topicStatus, docRefs,
            topicPriority, index, labelList,
            modifiedData, dueDate, assignee,
            description, stage, relatedTopics)
    return topic


def buildHeader(headerDict):

    fileDict = headerDict["File"]
    filename = getOptionalFromDict(fileDict, "Filename", None)
    filedate = getOptionalFromDict(fileDict, "Date", None)
    if filedate:
        filedate = dateutil.parser.parse(filedate)

    reference = getOptionalFromDict(fileDict, "Reference", None)
    if reference:
        reference = Uri(reference)

    ifcProjectId = getOptionalFromDict(fileDict, "@IfcProject", None)
    if ifcProjectId:
        ifcProjectId = UUID(ifcProjectId)

    ifcSpatialStructureElement = getOptionalFromDict(fileDict,
            "@IfcSpatialStructureElement", None)
    if ifcSpatialStructureElement:
        ifcSpatialStructureElement = UUID(ifcSpatialStructureElement)

    isExternal = getOptionalFromDict(fileDict, "@isExternal", True)

    header = Header(ifcProjectId, ifcSpatialStructureElement,
            isExternal, filename, date, reference)
    return header


def buildViewpointReference(viewpointDict):

    id = UUID(viewpointDict["@Guid"])
    viewpointFile = getOptionalFromDict(viewpointDict, "Viewpoint", None)
    if viewpointFile:
        viewpointFile = Uri(viewpointFile)

    snapshotFile = getOptionalFromDict(viewpointDict, "Snapshot", None)
    if snapshotFile:
        snapshotFile = Uri(snapshotFile)

    index = getOptionalFromDict(viewpointDict, "Index", 0)

    vpReference = ViewpointReference(id, viewpointFile, snapshotFile, index)
    return vpReference


#TODO: implement that function
def buildMarkup(markupFilePath: str, markupSchemaPath: str,
        viewpoints: List[viewpoint.Viewpoint],
        snapshots: List[Uri]):

    markupSchema = XMLSchema(markupSchemaPath)
    markupDict = markupSchema.to_dict(markupFilePath)

    pprint.pprint(markupDict)
    if "Comment" in markupDict:
        comments = list()
        for commentDict in markupDict["Comment"]:
            comment = buildComment(commentDict)
            comments.append(comment)

    topicDict = markupDict["Topic"]
    topic = buildTopic(topicDict)

    headerDict = getOptionalFromDict(markupDict, "Header", None)
    header = None
    # there may be instances that define an empty header element
    if headerDict and len(headerDict) > 0:
        header = buildHeader(headerDict)

    viewpointList = getOptionalFromDict(markupDict, "Viewpoints", list())
    viewpoints = [ buildViewpointReference(vpDict)
                    for vpDict in viewpointList ]

    markup = Markup(header, topic, comments, viewpoints)
    return markup


#TODO: implement that function
def buildViewpoint(viewpointFilePath: str, viewpointSchemaPath: str):
    pass


def validateFile(validateFilePath: str,
        schemaPath: str,
        bcfFile: str):

    """
    Validates `validateFileName` against the XSD file referenced by
    `schemaPath`. If successful an empty string is returned, else an error
    string is returned.
    """

    schema = XMLSchema(schemaPath)
    try:
        schema.validate(validateFilePath)
    except Exception as e:
        # get parent directory of file, useful for the user if the file is a
        # markup.bcf file inside some topic
        parentDir = os.path.abspath(os.path.join(validateFilePath, os.pardir))
        return "{} file inside {} of {} could not be validated against"\
                " {}\nError:{}".format(validateFilePath, parentDir, bcfFile,
                    os.path.basename(schemaPath), str(e))

    return ""


def readBcfFile(bcfFile: str):

    """
    Reads the bcfFile into the memory. Before each file is parsed into the class
    structure it gets validated against its corresponding XSD file.
    If parsing went successful then a value other than a object of type Project
    is returned.
    """

    tmpDir = util.getSystemTmp()
    (projectSchemaPath, extensionsSchemaPath,\
        markupSchemaPath, versionSchemaPath,\
        visinfoSchemaPath) = util.downloadToDir(tmpDir)
    bcfExtractedPath = extractFileToTmp(bcfFile)

    # before a file gets read into memory it needs to get validated (i.e.:
    # before the corresponding build* function is called, validate with
    # xmlschema)
    ### Check version ###
    versionFilePath = os.path.join(bcfExtractedPath, "bcf.version")
    if not os.path.exists(versionFilePath):
        print("No bcf.version file found in {}. This file is not optional.",
                file=sys.stderr)
        return None
    error = validateFile(versionFilePath, versionSchemaPath, bcfFile)
    if error != "":
        pprint.pprint(error, file=sys.stderr)
        return None
    version = getVersion(bcfExtractedPath, versionSchemaPath)
    if version not in SUPPORTED_VERSIONS:
        pprint.pprint("BCF version {} is not supported by this plugin. Supported"\
                "versions are: {}".format(version, SUPPORTED_VERSIONS),
                file=sys.stderr)
        return None

    ### Validate project and build ###
    # project.bcfp is optional, but it is necessary for the data model
    proj = project.Project(UUID(int=0))
    projectFilePath = os.path.join(bcfExtractedPath, "project.bcfp")
    if os.path.exists(projectFilePath):
        error = validateFile(projectFilePath, projectSchemaPath, bcfFile)
        if error != "":
            pprint.pprint(error, file=sys.stderr)
            return None
        proj = buildProject(projectFilePath, projectSchemaPath)

    ### Iterate over the topic directories ###
    topicDirectories = util.getDirectories(bcfExtractedPath)
    pprint.pprint(topicDirectories)
    for topic in topicDirectories:
        ### Validate all viewpoint files in the directory, and build them ###
        topicDir = os.path.join(bcfExtractedPath, topic)
        viewpointFiles = getFileListByExtension(topicDir, ".bcfv")
        errorList = [ validateFile(os.path.join(topicDir, viewpointFile),
                                    visinfoSchemaPath,
                                    bcfFile)
                      for viewpointFile in viewpointFiles
                    ]
        # truncate to only contain non-empty strings == error messages
        errorList = list(filter(lambda item: item != "", errorList))
        if len(errorList) > 0:
            print("One or more viewpoint.bcfv files could not be validated.")
            for error in errorList:
                pprint.pprint(error)
            continue
        viewpoints = [ buildViewpoint(viewpointFile, visinfoSchemaPath)
                            for viewpointFile in viewpointFiles ]

        # get list of all snapshots in the directory
        snapshots = getFileListByExtension(topicDir, ".png")

        markupFilePath = os.path.join(topicDir, "markup.bcf")
        print("looking into topic {}".format(topicDir))
        error = validateFile(markupFilePath, markupSchemaPath, bcfFile)
        if error != "":
            print(error, file=sys.stderr)
            return None
        markup = buildMarkup(markupFilePath, markupSchemaPath, viewpoints, snapshots)

        # add the finished markup object to the project
        proj.topicList.append(markup)

    return proj


if __name__ == "__main__":
    #extractedProjectPath = extractFileToTmp(sys.argv[1])
    project = readBcfFile(sys.argv[1])
    print(project)