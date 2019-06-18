import os
import sys
import copy
import pprint
import difflib
import unittest
import xmlschema
import dateutil.parser
import xml.etree.ElementTree as ET

from uuid import UUID
from shutil import rmtree
from shutil import copyfile
from xmlschema import XMLSchemaValidationError

sys.path.insert(0, "../")
import bcf.uri as uri
import bcf.util as util
import bcf.topic as topic
import bcf.reader as reader
import bcf.writer as writer
import bcf.markup as markup
import interfaces.state as s
import bcf.project as project
import bcf.threedvector as tdv
import bcf.viewpoint as viewpoint
import bcf.modification as modification
import interfaces.hierarchy as hierarchy

def setupBCFFile(testFile, testFileDir, testTopicDir, testBCFName):

    os.system("cp {} {}/{}/markup.bcf".format(testFile,
        testFileDir, testTopicDir))
    os.system("cd ./writer_tests && zip {} {}/markup.bcf".format(testBCFName,
        testTopicDir))

    return os.path.join(testFileDir, testBCFName)


def compareFiles(checkFile, testFileDir, testTopicDir, testBCFName):

    testFilePath = os.path.join(util.getSystemTmp(), testBCFName,
                testTopicDir)
    if checkFile.startswith("markup"):
        testFilePath = os.path.join(testFilePath, "markup.bcf")
    elif checkFile.startswith("viewpoint"):
        testFilePath = os.path.join(testFilePath, "viewpoint.bcfv")

    checkFilePath = os.path.join(testFileDir, checkFile)

    with open(testFilePath, 'r') as testFile:
        with open(checkFilePath, 'r') as checkFile:
            testFileText = testFile.readlines()
            if testFileText[-1][-1] != "\n":
                testFileText[-1] += "\n"
            checkFileText = checkFile.readlines()
            differ = difflib.Differ(charjunk=difflib.IS_CHARACTER_JUNK)
            resultDiffText = list(differ.compare(testFileText, checkFileText))
            resultList = [ False for item in resultDiffText if item[0] != ' ' ]

            if len(resultList)>0:
                return (False, resultDiffText)
            else:
                return (True, None)


class AddElementTests(unittest.TestCase):

    def setUp(self):
        self.testFileDir = "./writer_tests"
        self.testTopicDir = "2e92784b-80fc-4e0e-ac02-b424dfd8e664"
        self.testBCFName = "Issues-Example.bcf"
        self.markupDestDir = os.path.join(util.getSystemTmp(), self.testBCFName,
                self.testTopicDir)
        self.testFiles = ["markup_add_comment_test.bcf",
                "markup_add_comment_modification_test.bcf",
                "markup_add_lone_viewpoint_test.bcf",
                "markup_add_full_viewpoint_test.bcf",
                "", # dummy element to keep both lists equal in length
                "markup_add_file_test.bcf",
                "markup_add_file_attribute_test.bcf",
                "markup_add_file_attribute2_test.bcf",
                "markup_add_doc_ref_attribute_test.bcf",
                "markup_add_bim_snippet_attribute_test.bcf",
                "markup_add_label_test.bcf",
                "markup_add_assigned_to_test.bcf"
                ]
        self.checkFiles = ["markup_add_comment_check.bcf",
                "markup_add_comment_modification_check.bcf",
                "markup_add_lone_viewpoint_check.bcf",
                "markup_add_full_viewpoint_check.bcf",
                "viewpoint_add_full_viewpoint_check.bcfv",
                "markup_add_file_check.bcf",
                "markup_add_file_attribute_check.bcf",
                "markup_add_file_attribute2_check.bcf",
                "markup_add_doc_ref_attribute_check.bcf",
                "markup_add_bim_snippet_attribute_check.bcf",
                "markup_add_label_check.bcf",
                "markup_add_assigned_to_check.bcf"
                ]
        self.testFileDestinations = [os.path.join(self.markupDestDir, "markup.bcf"),
                os.path.join(self.markupDestDir, "viewpoint.bcfv"),
                os.path.join(self.markupDestDir, "viewpoint2.bcfv")]


    def test_add_comment(self):
        """
        Tests the addition of a comment.
        """

        srcFilePath = os.path.join(self.testFileDir, self.testFiles[0])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        project = reader.readBcfFile(testFile)

        markup = project.topicList[0]
        prototypeComment = copy.deepcopy(markup.comments[0])
        prototypeComment.comment = "hello this is me mario!"
        prototypeComment.state = s.State.States.ADDED
        markup.comments.append(prototypeComment)

        writer.addElement(prototypeComment)

        (equal, diff) = compareFiles(self.checkFiles[0], self.testFileDir, self.testTopicDir, self.testBCFName)
        if not equal:
            wrongFileDestination = os.path.join(self.testFileDir, "error_files",
                    "markup_add_comment.bcf")
            copyfile(self.testFileDestinations[0], wrongFileDestination)
            print("writer_tests.{}(): copied erroneous file to"\
                    " {}".format(self.test_add_file.__name__,
                        wrongFileDestination))
            print("Following is the diff between the file that was generated"\
                    " and the prepared file:")
            pprint.pprint(diff)
        self.assertTrue(equal)


    def test_add_comment_modification(self):
        """
        Tests the addition of modification data to an existing comment
        """

        srcFilePath = os.path.join(self.testFileDir, self.testFiles[1])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        project = reader.readBcfFile(testFile)

        markup = project.topicList[0]
        comment = markup.comments[0]
        modifiedDate = dateutil.parser.parse("2014-10-16T13:10:56+00:00")
        modifiedAuthor = "fleopard@bim.col"
        mod = modification.Modification(author = modifiedAuthor,
                date = modifiedDate,
                modType = modification.ModificationType.MODIFICATION)
        comment.lastModification = mod
        comment.lastModification.state = s.State.States.ADDED
        writer.addElement(comment.lastModification._author)
        writer.addElement(comment.lastModification._date)

        (equal, diff) = compareFiles(self.checkFiles[1], self.testFileDir, self.testTopicDir, self.testBCFName)
        if not equal:
            wrongFileDestination = os.path.join(self.testFileDir, "error_files",
                    "markup_add_comment_modification.bcf")
            copyfile(self.testFileDestinations[0], wrongFileDestination)
            print("writer_tests.{}(): copied erroneous file to"\
                    " {}".format(self.test_add_file.__name__,
                        wrongFileDestination))
            print("Following is the diff between the file that was generated"\
                    " and the prepared file:")
            pprint.pprint(diff)
        self.assertTrue(equal)


    def test_add_viewpointreference(self):
        """
        Tests whether a viewpoint reference can be added without having a new
        viewpoint file created.
        """

        srcFilePath = os.path.join(self.testFileDir, self.testFiles[2])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        project = reader.readBcfFile(testFile)

        markup = project.topicList[0]
        prototypeViewpointRef = copy.deepcopy(markup.viewpoints[0])
        prototypeViewpointRef.id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        prototypeViewpointRef.viewpoint = None
        prototypeViewpointRef.state = s.State.States.ADDED
        markup.viewpoints.append(prototypeViewpointRef)
        writer.addElement(prototypeViewpointRef)

        (equal, diff) = compareFiles(self.checkFiles[2], self.testFileDir, self.testTopicDir, self.testBCFName)
        if not equal:
            wrongFileDestination = os.path.join(self.testFileDir, "error_files",
                    "markup_add_lone_viewpoint.bcf")
            copyfile(self.testFileDestinations[0], wrongFileDestination)
            print("writer_tests.{}(): copied erroneous file to"\
                    " {}".format(self.test_add_file.__name__,
                        wrongFileDestination))
            print("writer_tests.{}(): Following is the diff between the file that was generated"\
                " and the prepared file:".format(
                    self.test_add_viewpointreference.__name__))
            pprint.pprint(diff)
        self.assertTrue(equal)


    def test_add_viewpoint(self):
        """
        Tests the correct addition of a complete new viewpoint including a new
        viewpoint reference in markup
        """

        srcFilePath = os.path.join(self.testFileDir, self.testFiles[3])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        project = reader.readBcfFile(testFile)

        markup = project.topicList[0]
        prototypeViewpointRef = copy.deepcopy(markup.viewpoints[0])
        prototypeViewpointRef.file = "viewpoint2.bcfv"
        prototypeViewpointRef.state = s.State.States.ADDED
        prototypeViewpointRef.viewpoint.state = s.State.States.ADDED
        markup.viewpoints.append(prototypeViewpointRef)
        writer.addElement(prototypeViewpointRef)

        (vpRefEqual, vpRefDiff) = compareFiles(self.checkFiles[3], self.testFileDir, self.testTopicDir, self.testBCFName)
        (vpEqual, vpDiff) = compareFiles(self.checkFiles[4], self.testFileDir, self.testTopicDir, self.testBCFName)
        if not vpRefEqual:
            wrongFileDestination = os.path.join(self.testFileDir, "error_files",
                    "markup_add_full_viewpoint.bcf")
            copyfile(self.testFileDestinations[0], wrongFileDestination)
            print("writer_tests.{}(): copied erroneous file to"\
                    " {}".format(self.test_add_file.__name__,
                        wrongFileDestination))
            print("writer_tests.{}(): Following is the diff between the file that was generated"\
                " and the prepared file:".format(
                        self.test_add_viewpoint.__name__))
            pprint.pprint(vpRefDiff)

        if not vpEqual:
            wrongFileDestination = os.path.join(self.testFileDir, "error_files",
                    "viewpoint_add_full_viewpoint.bcfv")
            copyfile(self.testFileDestinations[2], wrongFileDestination)
            print("writer_tests.{}(): copied erroneous file to"\
                    " {}".format(self.test_add_file.__name__,
                        wrongFileDestination))
            print("writer_tests.{}(): Following is the diff between the file that was generated"\
                " and the prepared file:".format(
                        self.test_add_viewpoint.__name__))
            pprint.pprint(vpDiff)
        self.assertTrue(vpRefEqual and vpEqual)


    def test_add_file(self):
        """
        Tests the addition of a file element in the header node
        """

        srcFilePath = os.path.join(self.testFileDir, self.testFiles[5])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        p = reader.readBcfFile(testFile)

        m = p.topicList[0]
        header = m.header
        newFile = markup.HeaderFile(ifcProjectId = "abcdefghij",
            ifcSpatialStructureElement = "klmnopqrs",
            isExternal = False,
            filename = "this is some file name",
            time = dateutil.parser.parse("2014-10-16T13:10:56+00:00"),
            reference = "/path/to/the/file",
            containingElement = header,
            state = s.State.States.ADDED)
        header.files.append(newFile)
        project.debug("writer_tests.{}(): type of newFile is"
                " {}".format(self.test_add_file.__name__,
                    type(newFile)))

        writer.addElement(newFile)

        (equal, diff) = compareFiles(self.checkFiles[5], self.testFileDir, self.testTopicDir, self.testBCFName)
        if not equal:
            wrongFileDestination = os.path.join(self.testFileDir, "error_files",
                    "markup_add_file.bcf")
            copyfile(self.testFileDestinations[0], wrongFileDestination)
            print("writer_tests.{}(): copied erroneous file to"\
                    " {}".format(self.test_add_file.__name__,
                        wrongFileDestination))
            print("writer_tests.{}(): Following is the diff between the file that was generated"\
                " and the prepared file:".format(
                    self.test_add_viewpointreference.__name__,
                    wrongFileDestination))
            pprint.pprint(diff)
        self.assertTrue(equal)


    def test_add_file_attributes(self):
        """
        Tests the addition of the optional attributes to one of the file nodes
        """
        srcFilePath = os.path.join(self.testFileDir, self.testFiles[6])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        p = reader.readBcfFile(testFile)

        m = p.topicList[0]
        file = m.header.files[0]
        file.ifcProjectId = "aaaabbbbcccc"
        file._ifcProjectId.state = s.State.States.ADDED
        writer.addElement(file._ifcProjectId)

        (equal, diff) = compareFiles(self.checkFiles[6], self.testFileDir, self.testTopicDir, self.testBCFName)
        if not equal:
            wrongFileDestination = os.path.join(self.testFileDir, "error_files",
                    "markup_add_file_attribute.bcf")
            copyfile(self.testFileDestinations[0], wrongFileDestination)
            print("writer_tests.{}(): copied erroneous file to"\
                    " {}".format(self.test_add_file.__name__,
                        wrongFileDestination))
            print("writer_tests.{}(): Following is the diff between the file that was generated"\
                " and the prepared file:".format(
                    self.test_add_viewpointreference.__name__,
                    wrongFileDestination))
            pprint.pprint(diff)
        self.assertTrue(equal)


    def test_add_file_attributes2(self):
        """
        Tests the addition of the optional attributes to one of the file nodes
        """
        srcFilePath = os.path.join(self.testFileDir, self.testFiles[7])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        p = reader.readBcfFile(testFile)

        m = p.topicList[0]
        file = m.header.files[0]
        file.ifcSpatialStructureElement = "aaaabbbbcccc"
        file._ifcSpatialStructureElement.state = s.State.States.ADDED
        writer.addElement(file._ifcSpatialStructureElement)

        (equal, diff) = compareFiles(self.checkFiles[7], self.testFileDir, self.testTopicDir, self.testBCFName)
        if not equal:
            wrongFileDestination = os.path.join(self.testFileDir, "error_files",
                    "markup_add_file_attribute2.bcf")
            copyfile(self.testFileDestinations[0], wrongFileDestination)
            print("writer_tests.{}(): copied erroneous file to"\
                    " {}".format(self.test_add_file.__name__,
                        wrongFileDestination))
            print("writer_tests.{}(): Following is the diff between the file that was generated"\
                " and the prepared file:".format(
                    self.test_add_viewpointreference.__name__,
                    wrongFileDestination))
            pprint.pprint(diff)
        self.assertTrue(equal)


    def test_add_documentReference_attributes(self):
        """
        Tests the addition of the optional attributes to one of the document
        reference nodes.
        """
        srcFilePath = os.path.join(self.testFileDir, self.testFiles[8])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        p = reader.readBcfFile(testFile)

        docRef = p.topicList[0].topic.refs[0]
        docRef.guid = "98b5802c-4ca0-4032-9128-b9c606955c4f"
        docRef._guid.state = s.State.States.ADDED
        writer.addElement(docRef._guid)

        (equal, diff) = compareFiles(self.checkFiles[8], self.testFileDir, self.testTopicDir, self.testBCFName)
        if not equal:
            wrongFileDestination = os.path.join(self.testFileDir, "error_files",
                    "markup_add_doc_ref_attribute.bcf")
            copyfile(self.testFileDestinations[0], wrongFileDestination)
            print("writer_tests.{}(): copied erroneous file to"\
                    " {}".format(self.test_add_file.__name__,
                        wrongFileDestination))
            print("writer_tests.{}(): Following is the diff between the file that was generated"\
                " and the prepared file:".format(
                    self.test_add_viewpointreference.__name__,
                    wrongFileDestination))
            pprint.pprint(diff)
        self.assertTrue(equal)


    def test_add_bimSnippet_attribute(self):
        """
        Tests the addition of the optional attribute of BimSnippet
        """
        srcFilePath = os.path.join(self.testFileDir, self.testFiles[9])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        p = reader.readBcfFile(testFile)

        bimSnippet = p.topicList[0].topic.bimSnippet
        bimSnippet.external = True
        bimSnippet.state = s.State.States.ADDED
        writer.addElement(bimSnippet._external)

        (equal, diff) = compareFiles(self.checkFiles[9], self.testFileDir, self.testTopicDir, self.testBCFName)
        if not equal:
            wrongFileDestination = os.path.join(self.testFileDir, "error_files",
                    "markup_add_bim_snippet.bcf")
            copyfile(self.testFileDestinations[0], wrongFileDestination)
            print("writer_tests.{}(): copied erroneous file to"\
                    " {}".format(self.test_add_file.__name__,
                        wrongFileDestination))
            print("writer_tests.{}(): Following is the diff between the file that was generated"\
                " and the prepared file:".format(
                    self.test_add_viewpointreference.__name__,
                    wrongFileDestination))
            pprint.pprint(diff)
        self.assertTrue(equal)


    def test_add_label(self):
        """
        Tests the addition of a label
        """
        srcFilePath = os.path.join(self.testFileDir, self.testFiles[10])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        p = reader.readBcfFile(testFile)

        t = p.topicList[0].topic
        newLabel = "Hello"
        t.labels.append(newLabel)
        writer.addElement(t.labels[-1])

        (equal, diff) = compareFiles(self.checkFiles[10], self.testFileDir, self.testTopicDir, self.testBCFName)
        if not equal:
            wrongFileDestination = os.path.join(self.testFileDir, "error_files",
                    "markup_add_label.bcf")
            copyfile(self.testFileDestinations[0], wrongFileDestination)
            print("writer_tests.{}(): copied erroneous file to"\
                    " {}".format(self.test_add_file.__name__,
                        wrongFileDestination))
            print("writer_tests.{}(): Following is the diff between the file that was generated"\
                " and the prepared file:".format(
                    self.test_add_viewpointreference.__name__,
                    wrongFileDestination))
            pprint.pprint(diff)
        self.assertTrue(equal)


    def test_add_assignedTo(self):
        """
        Tests the addition of the AssignedTo node to a topic
        """

        srcFilePath = os.path.join(self.testFileDir, self.testFiles[11])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        p = reader.readBcfFile(testFile)

        t = p.topicList[0].topic
        t.assignee = "a@b.c"
        t._assignee.state = s.State.States.ADDED
        writer.addElement(t._assignee)

        (equal, diff) = compareFiles(self.checkFiles[11], self.testFileDir, self.testTopicDir, self.testBCFName)
        if not equal:
            wrongFileDestination = os.path.join(self.testFileDir, "error_files",
                    "markup_add_assignedTo.bcf")
            copyfile(self.testFileDestinations[0], wrongFileDestination)
            print("writer_tests.{}(): copied erroneous file to"\
                    " {}".format(self.test_add_file.__name__,
                        wrongFileDestination))
            print("writer_tests.{}(): Following is the diff between the file that was generated"\
                " and the prepared file:".format(
                    self.test_add_viewpointreference.__name__,
                    wrongFileDestination))
            pprint.pprint(diff)
        self.assertTrue(equal)


class GetEtElementFromFileTests(unittest.TestCase):

    def setUp(self):
        self.testFileDir = "./writer_tests"
        self.testTopicDir = "2e92784b-80fc-4e0e-ac02-b424dfd8e664"
        self.testBCFName = "Issues-Example.bcf"
        self.markupDestDir = os.path.join(util.getSystemTmp(), self.testBCFName,
                self.testTopicDir)
        self.testFiles = ["markup_find_comment_test.bcf",
                "markup_find_comment2_test.bcf",
                "markup_find_label_by_text_test.bcf",
                "markup_find_file_by_attribute_test.bcf"
                ]
        self.checkFiles = ["markup_find_comment_check.bcf"
                ]
        self.testFileDestinations = [os.path.join(self.markupDestDir, "markup.bcf"),
                os.path.join(self.markupDestDir, "viewpoint.bcfv"),
                os.path.join(self.markupDestDir, "viewpoint2.bcfv")]


    def test_findComment(self):
        """
        Tests whether a comment can be found by its children
        """

        srcFilePath = os.path.join(self.testFileDir, self.testFiles[0])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        p = reader.readBcfFile(testFile)

        xmlfile = ET.parse(self.testFileDestinations[0])
        xmlroot = xmlfile.getroot()

        commentToFind = p.topicList[0].comments[1]
        finding = writer.getEtElementFromFile(xmlroot, commentToFind)

        expectedComment = list(xmlroot)[3]
        project.debug("writer_tests.test_findComment(): found comment:"\
                "\n\t{}\nand expected comment\n{}"\
                "\n=====".format(ET.tostring(finding),
                    ET.tostring(expectedComment)))

        self.assertEqual(ET.tostring(expectedComment), ET.tostring(finding))


    def test_findComment2(self):
        """
        Tests whether the right comment is found if the text of one child
        differs only by one character
        """

        srcFilePath = os.path.join(self.testFileDir, self.testFiles[1])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        p = reader.readBcfFile(testFile)

        xmlfile = ET.parse(self.testFileDestinations[0])
        xmlroot = xmlfile.getroot()

        expectedComment = list(xmlroot)[3]

        commentToFind = p.topicList[0].comments[1]
        finding = writer.getEtElementFromFile(xmlroot, commentToFind)

        project.debug("writer_tests.test_findComment2(): found comment:"\
                "\n\t{}\nand expected comment\n{}"\
                "\n=====".format(ET.tostring(finding),
                    ET.tostring(expectedComment)))

        self.assertEqual(ET.tostring(expectedComment), ET.tostring(finding))


    def test_findLabelByText(self):

        """
        Tests whether a label can be found just by the text it contains.
        """

        srcFilePath = os.path.join(self.testFileDir, self.testFiles[2])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        p = reader.readBcfFile(testFile)

        xmlfile = ET.parse(self.testFileDestinations[0])
        xmlroot = xmlfile.getroot()

        topicEt = list(xmlroot)[1]
        expectedLabel = list(topicEt)[5]

        labelToFind = p.topicList[0].topic.labels[2]
        finding = writer.getEtElementFromFile(xmlroot, labelToFind)

        project.debug("writer_tests.test_findLabelByText(): found label:"\
                "\n\t{}\nand expected label\n{}"\
                "\n=====".format(ET.tostring(finding),
                    ET.tostring(expectedLabel)))

        self.assertEqual(ET.tostring(finding), ET.tostring(expectedLabel))


    def test_findFileByAttribute(self):

        """
        Tests whether a file node can be found solely by its specified
        attributes.
        """

        srcFilePath = os.path.join(self.testFileDir, self.testFiles[3])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        p = reader.readBcfFile(testFile)

        xmlfile = ET.parse(self.testFileDestinations[0])
        xmlroot = xmlfile.getroot()

        headerEt = list(xmlroot)[0]
        expectedFile = list(headerEt)[3]

        fileToFind = p.topicList[0].header.files[3]
        finding = writer.getEtElementFromFile(xmlroot, fileToFind)

        project.debug("writer_tests.test_findFileByAttribute(): found file:"\
                "\n\t{}\nand expected file\n{}"\
                "\n=====".format(ET.tostring(finding),
                    ET.tostring(expectedFile)))

        self.assertEqual(ET.tostring(finding), ET.tostring(expectedFile))


def handleFileCheck(expectedFile, fileName, testFileDir, testTopicDir, testBCFName):

    """
    Compares the working file with `expectedFile`. If they are different then
    the working file is copied to `testFileDir/error.bcf` for human
    inspection. True is returned if both files are equal, false otherwise.
    """

    (equal, diff) = compareFiles(expectedFile, testFileDir, testTopicDir, testBCFName)
    if not equal:
        wrongFileDestination = os.path.join(testFileDir,
                "error.bcf")
        testFilePath = os.path.join(util.getSystemTmp(), testBCFName,
                testTopicDir, fileName)
        copyfile(testFilePath, wrongFileDestination)
        print("writer_tests.{}(): copied erroneous file to"\
                " {}".format(handleFileCheck.__name__,
                    wrongFileDestination))
        print("writer_tests.{}(): Following is the diff between the file that was generated"\
            " and the prepared file:".format(
                handleFileCheck.__name__,
                wrongFileDestination))
        pprint.pprint(diff)

    return equal


class DeleteElementTests(unittest.TestCase):

    def setUp(self):
        self.testFileDir = "./writer_tests"
        self.testTopicDir = "2e92784b-80fc-4e0e-ac02-b424dfd8e664"
        self.testBCFName = "Issues-Example.bcf"
        self.markupDestDir = os.path.join(util.getSystemTmp(), self.testBCFName,
                self.testTopicDir)
        self.testFiles = ["markup_delete_comment_test.bcf",
                "markup_delete_label_test.bcf",
                "markup_delete_ifcproject_test.bcf"
                ]
        self.checkFiles = ["markup_delete_comment_check.bcf",
                "markup_delete_label_check.bcf",
                "markup_delete_ifcproject_check.bcf"
                ]
        self.testFileDestinations = [os.path.join(self.markupDestDir, "markup.bcf"),
                os.path.join(self.markupDestDir, "viewpoint.bcfv"),
                os.path.join(self.markupDestDir, "viewpoint2.bcfv")]


    def test_deleteComment(self):

        srcFilePath = os.path.join(self.testFileDir, self.testFiles[0])
        testFile = setupBCFFile(srcFilePath, self.testFileDir, self.testTopicDir, self.testBCFName)
        p = reader.readBcfFile(testFile)

        commentToDelete = p.topicList[0].comments[0]
        project.debug("Starting to delete element {}".format(commentToDelete))
        writer.deleteElement(commentToDelete)

        equal = handleFileCheck(self.checkFiles[0], "markup.bcf", self.testFileDir,
                self.testTopicDir, self.testBCFName)

        self.assertTrue(equal)


    def test_deleteLabel(self):
        pass

    def test_deleteIfcProject(self):
        pass

    def test_deleteFile(self):
        pass

    def test_deleteViewpoint(self):
        pass

    def test_deleteViewpointReference(self):
        pass


if __name__ == "__main__":
    unittest.main()
